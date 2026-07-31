"""
Goodness of Pronunciation (GOP) scoring engine.

Computes per-phoneme GOP scores using frame-level log-posteriors from the
wav2vec2-CTC phoneme recognizer, aligned against the expected (reference)
phoneme sequence.

GOP formula (standard from Kaldi/wav2vec2-CTC literature):
  For each expected phoneme p at time-aligned frames [t_start, t_end]:
    GOP(p) = (1/T) * sum_{t=t_start}^{t_end} log P(p | x_t)
  where:
    - P(p | x_t) is the posterior probability of phoneme p at frame t
    - T = number of frames in the segment
    - x_t is the acoustic feature at frame t

  A higher (less negative) GOP score means better pronunciation.
  The gap between GOP(p) and max_q GOP(q) tells us severity of mispronunciation.

Design:
  - Uses forced alignment timestamps from WhisperX to determine frame ranges
    for each word/phoneme segment.
  - The wav2vec2-CTC model provides the frame-level posteriors.
  - No randomness: GOP is fully deterministic for the same audio input.
"""

from dataclasses import dataclass, field

import numpy as np

from app.core.logging import get_logger
from app.modules.scoring.phoneme_recognizer import (
    PhonemeRecognitionResult,
    get_phoneme_id,
    get_vocab,
)

logger = get_logger(__name__)

# Number of CTC frames per second (wav2vec2 outputs ~50 frames/sec for 16kHz audio)
FRAMES_PER_SECOND = 50.0


@dataclass
class PhonemeGOPScore:
    """GOP score for a single phoneme within a word."""
    phoneme: str
    gop_score: float  # log-posterior (negative, higher = better)
    max_posterior_phoneme: str  # which phoneme the model thinks is most likely
    max_posterior_score: float  # the best log-posterior at these frames
    gap: float  # max_posterior_score - gop_score (smaller = better pronunciation)


@dataclass
class WordGOPResult:
    """GOP analysis for a single word."""
    word: str
    start: float  # timestamp in seconds
    end: float  # timestamp in seconds
    phoneme_scores: list[PhonemeGOPScore] = field(default_factory=list)
    word_gop_score: float = 0.0  # mean GOP across phonemes in this word
    confidence: float = 0.0  # original ASR confidence (preserved for comparison)


def compute_gop_scores(
    recognition_result: PhonemeRecognitionResult,
    words: list[dict],
    reference_phonemes_per_word: list[list[str]],
) -> list[WordGOPResult]:
    """
    Compute GOP scores for each word given:
      - The frame-level log-probs from the wav2vec2-CTC model
      - Word timestamps from WhisperX alignment
      - Reference (expected) phoneme sequences per word

    Args:
        recognition_result: Output from phoneme_recognizer.get_frame_log_probs()
        words: List of {word, start, end, confidence} from WhisperX
        reference_phonemes_per_word: List of phoneme lists, one per word
            (from phonemizer / get_reference_phonemes)

    Returns:
        List of WordGOPResult with per-phoneme GOP scores.
    """
    log_probs = recognition_result.log_probs  # (num_frames, vocab_size)
    num_frames = log_probs.shape[0]
    vocab = get_vocab()

    results = []

    for word_idx, (word_info, expected_phonemes) in enumerate(
        zip(words, reference_phonemes_per_word)
    ):
        word_text = word_info.get("word", "")
        start_time = word_info.get("start", 0.0)
        end_time = word_info.get("end", 0.0)
        confidence = word_info.get("confidence", 0.0)

        # Pre-process: merge length marks with preceding vowels for vocab lookup
        expected_phonemes = _merge_length_marks(expected_phonemes, vocab)

        # Convert timestamps to frame indices
        start_frame = int(start_time * FRAMES_PER_SECOND)
        end_frame = int(end_time * FRAMES_PER_SECOND)

        # Clamp to valid range
        start_frame = max(0, min(start_frame, num_frames - 1))
        end_frame = max(start_frame + 1, min(end_frame, num_frames))

        word_frames = end_frame - start_frame

        if not expected_phonemes or word_frames < 1:
            # No phonemes to score or no frames available
            results.append(WordGOPResult(
                word=word_text,
                start=start_time,
                end=end_time,
                phoneme_scores=[],
                word_gop_score=-10.0,  # worst-case default
                confidence=confidence,
            ))
            continue

        # Distribute frames roughly equally across expected phonemes
        phoneme_scores = []
        frames_per_phoneme = max(1, word_frames // len(expected_phonemes))

        for ph_idx, phoneme in enumerate(expected_phonemes):
            # Frame range for this phoneme
            ph_start = start_frame + ph_idx * frames_per_phoneme
            ph_end = min(ph_start + frames_per_phoneme, end_frame)

            if ph_start >= num_frames or ph_end <= ph_start:
                # Out of bounds — assign worst score
                phoneme_scores.append(PhonemeGOPScore(
                    phoneme=phoneme,
                    gop_score=-10.0,
                    max_posterior_phoneme="<unk>",
                    max_posterior_score=0.0,
                    gap=10.0,
                ))
                continue

            # Get the log-probs for these frames
            segment_log_probs = log_probs[ph_start:ph_end, :]  # (T, vocab_size)

            # Compute GOP: average log-posterior for the expected phoneme
            phoneme_id = _resolve_phoneme_id(phoneme, vocab)

            # Identify the blank/pad token (CTC blank is typically index 0)
            pad_id = vocab.get("<pad>", 0)

            if phoneme_id is not None:
                # Filter out blank-dominant frames for a more meaningful GOP score
                # CTC models produce blanks between phonemes — these frames
                # shouldn't count against pronunciation quality
                phoneme_log_probs = segment_log_probs[:, phoneme_id]
                blank_log_probs = segment_log_probs[:, pad_id]

                # Use frames where the expected phoneme has reasonable probability
                # OR where blank is not overwhelmingly dominant
                non_blank_mask = blank_log_probs < -0.5  # blank isn't > 60% likely
                if np.any(non_blank_mask):
                    gop_score = float(np.mean(phoneme_log_probs[non_blank_mask]))
                else:
                    # All frames are blank-dominant — use the best frame for this phoneme
                    gop_score = float(np.max(phoneme_log_probs))
            else:
                # Phoneme not in model vocabulary — use the max non-blank as fallback
                # Zero out blank column to find best real phoneme
                adjusted = segment_log_probs.copy()
                adjusted[:, pad_id] = -100.0
                gop_score = float(np.mean(np.max(adjusted, axis=1)))

            # Find the best (max posterior) NON-BLANK phoneme at these frames
            mean_log_probs = np.mean(segment_log_probs, axis=0)  # (vocab_size,)
            # Exclude special tokens from max search
            adjusted_mean = mean_log_probs.copy()
            for special_token in ("<pad>", "<s>", "</s>", "<unk>"):
                if special_token in vocab:
                    adjusted_mean[vocab[special_token]] = -100.0
            max_id = int(np.argmax(adjusted_mean))
            max_score = float(adjusted_mean[max_id])

            # Resolve max phoneme name
            from app.modules.scoring.phoneme_recognizer import get_id_to_phoneme_map
            id_to_phoneme = get_id_to_phoneme_map()
            max_phoneme = id_to_phoneme.get(max_id, "<unk>")

            # Gap: how much worse is the expected phoneme vs. the best
            gap = max_score - gop_score

            phoneme_scores.append(PhonemeGOPScore(
                phoneme=phoneme,
                gop_score=round(gop_score, 4),
                max_posterior_phoneme=max_phoneme,
                max_posterior_score=round(max_score, 4),
                gap=round(gap, 4),
            ))

        # Word-level GOP: mean of all phoneme GOP scores
        if phoneme_scores:
            word_gop = np.mean([ps.gop_score for ps in phoneme_scores])
        else:
            word_gop = -10.0

        results.append(WordGOPResult(
            word=word_text,
            start=start_time,
            end=end_time,
            phoneme_scores=phoneme_scores,
            word_gop_score=round(float(word_gop), 4),
            confidence=confidence,
        ))

    return results


def _merge_length_marks(phonemes: list[str], vocab: dict[str, int]) -> list[str]:
    """
    Merge standalone length marks (ː) with the preceding phoneme.

    Phonemizer often splits 'aː' into ['a', 'ː'], but the wav2vec2 model
    vocabulary has composite tokens like 'aː', 'iː', 'uː' etc.
    This merges them back so we get valid vocabulary lookups.
    """
    if not phonemes:
        return phonemes

    merged = []
    i = 0
    while i < len(phonemes):
        current = phonemes[i]

        # If current is a length mark and we have a preceding phoneme, merge
        if current == "ː" and merged:
            combined = merged[-1] + "ː"
            # Check if the combined form exists in vocab
            if combined in vocab:
                merged[-1] = combined
            # Otherwise just skip the length mark (it adds no scoring value)
            i += 1
            continue

        # If next is a length mark, try merging proactively
        if i + 1 < len(phonemes) and phonemes[i + 1] == "ː":
            combined = current + "ː"
            if combined in vocab:
                merged.append(combined)
                i += 2
                continue

        merged.append(current)
        i += 1

    return merged


def _resolve_phoneme_id(phoneme: str, vocab: dict[str, int]) -> int | None:
    """
    Try to find the phoneme in the model vocabulary.
    The wav2vec2-lv-60-espeak-cv-ft model uses espeak IPA symbols.
    Try exact match first, then common variants.
    """
    # Direct lookup
    if phoneme in vocab:
        return vocab[phoneme]

    # Try common variants
    variants = [
        phoneme.rstrip("ː"),  # remove length mark
        phoneme + "ː",  # add length mark
        phoneme.replace("ɡ", "g"),  # IPA g vs ASCII g
        phoneme.replace("g", "ɡ"),
        phoneme.replace("ɹ", "r"),  # r variants
        phoneme.replace("r", "ɹ"),
        phoneme.replace("ɚ", "ə"),  # rhotacized schwa → schwa
        phoneme.replace("ɝ", "ɜ"),  # rhotacized open-mid → plain
        phoneme.lower(),  # case insensitivity
    ]

    for v in variants:
        if v in vocab:
            return vocab[v]

    # Try single-char version of multi-char phonemes
    if len(phoneme) > 1:
        if phoneme[0] in vocab:
            return vocab[phoneme[0]]

    return None
