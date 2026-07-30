"""
Wav2Vec2-CTC phoneme recognizer — loaded once, cached in memory.

This module wraps the facebook/wav2vec2-lv-60-espeak-cv-ft model from
Hugging Face, which outputs IPA phoneme-level predictions with frame-level
posterior probabilities. These posteriors are what the GOP engine needs.

Design decisions:
  - Model loads once at first call and stays warm for the process lifetime.
  - Thread-safe: uses a module-level lock for lazy init.
  - Runs on CPU by default (configurable via settings).
  - Returns raw log-probabilities (logits → log_softmax) per frame so
    the GOP engine can compute Goodness of Pronunciation scores.
"""

import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.core.logging import get_logger
from app.core.settings import settings

logger = get_logger(__name__)

# Module-level singleton state
_model = None
_processor = None
_lock = threading.Lock()
_vocab_map: dict[str, int] = {}  # phoneme → token ID
_id_to_phoneme: dict[int, str] = {}  # token ID → phoneme

MODEL_NAME = "facebook/wav2vec2-lv-60-espeak-cv-ft"


@dataclass
class PhonemeRecognitionResult:
    """Result from the phoneme recognizer."""
    # Log-probabilities: shape (num_frames, vocab_size)
    log_probs: np.ndarray
    # Predicted phoneme sequence (greedy CTC decode)
    predicted_phonemes: list[str]
    # Sample rate the model expects
    sample_rate: int = 16000


def _ensure_model_loaded():
    """Lazy-load the model and processor. Thread-safe, happens only once."""
    global _model, _processor, _vocab_map, _id_to_phoneme

    if _model is not None:
        return

    with _lock:
        # Double-check after acquiring lock
        if _model is not None:
            return

        import torch
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

        logger.info(
            "phoneme_recognizer_loading",
            model=MODEL_NAME,
            device="cpu",
        )

        _processor = Wav2Vec2Processor.from_pretrained(MODEL_NAME)
        _model = Wav2Vec2ForCTC.from_pretrained(MODEL_NAME)
        _model.eval()  # inference mode, no dropout

        # Build vocabulary maps
        vocab = _processor.tokenizer.get_vocab()
        _vocab_map = {phoneme: idx for phoneme, idx in vocab.items()}
        _id_to_phoneme = {idx: phoneme for phoneme, idx in vocab.items()}

        logger.info(
            "phoneme_recognizer_loaded",
            model=MODEL_NAME,
            vocab_size=len(_vocab_map),
        )


def get_frame_log_probs(audio_array: np.ndarray, sample_rate: int = 16000) -> PhonemeRecognitionResult:
    """
    Run the wav2vec2-CTC model on audio and return frame-level log-probabilities.

    Args:
        audio_array: 1-D float32 numpy array of audio samples (mono, 16kHz).
        sample_rate: Sample rate of the input audio (must be 16000).

    Returns:
        PhonemeRecognitionResult with log_probs (frames × vocab) and predicted phonemes.
    """
    import torch

    _ensure_model_loaded()

    if sample_rate != 16000:
        raise ValueError(
            f"Wav2Vec2 phoneme model requires 16kHz audio, got {sample_rate}Hz. "
            "Resample before calling this function."
        )

    # Process audio through the model
    inputs = _processor(
        audio_array,
        sampling_rate=16000,
        return_tensors="pt",
        padding=True,
    )

    with torch.no_grad():
        outputs = _model(**inputs)
        logits = outputs.logits  # shape: (1, num_frames, vocab_size)

    # Convert to log-probabilities via log_softmax
    log_probs = torch.nn.functional.log_softmax(logits, dim=-1)
    log_probs_np = log_probs.squeeze(0).numpy()  # (num_frames, vocab_size)

    # Greedy CTC decode for reference
    predicted_ids = torch.argmax(logits, dim=-1).squeeze(0).tolist()
    predicted_phonemes = _ctc_greedy_decode(predicted_ids)

    return PhonemeRecognitionResult(
        log_probs=log_probs_np,
        predicted_phonemes=predicted_phonemes,
        sample_rate=16000,
    )


def get_phoneme_id(phoneme: str) -> int | None:
    """Look up the token ID for a given phoneme/IPA symbol in the model vocabulary."""
    _ensure_model_loaded()
    return _vocab_map.get(phoneme)


def get_vocab() -> dict[str, int]:
    """Return the full model vocabulary (phoneme → ID mapping)."""
    _ensure_model_loaded()
    return _vocab_map.copy()


def get_id_to_phoneme_map() -> dict[int, str]:
    """Return the reverse vocabulary (ID → phoneme mapping)."""
    _ensure_model_loaded()
    return _id_to_phoneme.copy()


def _ctc_greedy_decode(predicted_ids: list[int]) -> list[str]:
    """
    Greedy CTC decode: collapse repeated tokens and remove blanks.
    Returns a list of phoneme strings.
    """
    blank_id = _processor.tokenizer.pad_token_id if _processor.tokenizer.pad_token_id is not None else 0
    decoded = []
    prev_id = None

    for token_id in predicted_ids:
        if token_id == blank_id:
            prev_id = token_id
            continue
        if token_id != prev_id:
            phoneme = _id_to_phoneme.get(token_id, "")
            if phoneme and phoneme not in ("<pad>", "<s>", "</s>", "<unk>"):
                decoded.append(phoneme)
        prev_id = token_id

    return decoded


def load_audio_for_gop(audio_path: str | Path) -> tuple[np.ndarray, int]:
    """
    Load and prepare an audio file for the phoneme recognizer.
    Ensures mono, 16kHz, float32 format.

    Uses multiple backends for robustness (scipy for WAV, torchaudio as fallback).

    Returns:
        (audio_array, sample_rate) tuple.
    """
    import torch

    audio_path = str(audio_path)

    # Try scipy first (handles standard WAV files reliably without FFmpeg)
    try:
        import scipy.io.wavfile as wavfile
        sr, data = wavfile.read(audio_path)

        # Convert to float32 in [-1, 1] range
        if data.dtype == np.int16:
            audio_float = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            audio_float = data.astype(np.float32) / 2147483648.0
        elif data.dtype == np.float32:
            audio_float = data
        else:
            audio_float = data.astype(np.float32)

        # Convert to mono if stereo
        if audio_float.ndim > 1:
            audio_float = audio_float.mean(axis=1)

        # Resample to 16kHz if needed
        if sr != 16000:
            import torchaudio
            waveform = torch.from_numpy(audio_float).unsqueeze(0)
            resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=16000)
            waveform = resampler(waveform)
            audio_float = waveform.squeeze(0).numpy()
            sr = 16000

        return audio_float.astype(np.float32), sr

    except Exception as scipy_err:
        logger.debug("scipy_wav_load_failed", error=str(scipy_err), path=audio_path)

    # Fallback to torchaudio with explicit backend
    try:
        import torchaudio
        # Try soundfile backend (most reliable for WAV)
        waveform, sr = torchaudio.load(audio_path, backend="soundfile")
    except Exception:
        try:
            import torchaudio
            waveform, sr = torchaudio.load(audio_path)
        except Exception as e:
            raise RuntimeError(
                f"Could not load audio file {audio_path}. "
                f"Tried scipy and torchaudio. Error: {e}"
            )

    # Convert to mono if stereo
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    # Resample to 16kHz if needed
    if sr != 16000:
        import torchaudio
        resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=16000)
        waveform = resampler(waveform)
        sr = 16000

    # Convert to numpy float32
    audio_array = waveform.squeeze(0).numpy().astype(np.float32)

    return audio_array, sr


def is_model_loaded() -> bool:
    """Check if the phoneme recognizer model is currently loaded in memory."""
    return _model is not None
