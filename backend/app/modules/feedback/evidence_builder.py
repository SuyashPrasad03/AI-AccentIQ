"""
Phase 27 — Structured Evidence Builder

Takes the raw scoring data (GOP scores, error classifications, timing info)
and structures it into a clean evidence payload that the LLM feedback prompt
can consume. Every claim in the generated feedback must reference a specific
entry in this evidence.

Design:
  - Evidence is per-word: each word gets its own evidence bundle
  - Evidence includes: GOP scores per phoneme, classified error types,
    timing anomalies, substitution details
  - Confidence levels (High/Medium/Low) derived from GOP gap magnitude
"""

from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PhonemeEvidence:
    """Evidence for a single phoneme within a word."""
    phoneme: str
    gop_score: float
    gop_gap: float
    max_posterior_phoneme: str
    error_type: str  # correct|substitution|deletion|insertion|distortion
    error_confidence: float
    confidence_level: str  # High|Medium|Low


@dataclass
class WordEvidence:
    """Full evidence bundle for a single word."""
    word: str
    word_score: float  # normalized 0-100
    detected_issue: str  # correct|mispronounced|unclear|mistimed
    phoneme_evidence: list[PhonemeEvidence] = field(default_factory=list)
    expected_phonemes: list[str] = field(default_factory=list)
    substituted_as: list[str] = field(default_factory=list)
    error_type: str = "correct"
    error_type_confidence: float = 0.0
    confidence_level: str = "Medium"  # Overall word confidence


def build_word_evidence(word_data: dict, gop_raw: dict | None = None) -> WordEvidence:
    """
    Build a structured evidence bundle for a single word.

    Args:
        word_data: The word score dict from phoneme_analysis (MongoDB)
        gop_raw: Optional raw GOP data (from gop_raw_scores array)

    Returns:
        WordEvidence with all acoustic measurements structured for the LLM
    """
    word = word_data.get("word", "")
    word_score = word_data.get("word_score", 0.0)
    detected_issue = word_data.get("detected_issue", "correct")
    expected_phonemes = word_data.get("expected_phonemes", [])
    substituted_as = word_data.get("substituted_as", [])
    error_type = word_data.get("error_type", "correct")
    error_type_confidence = word_data.get("error_type_confidence", 0.0)

    # Build phoneme-level evidence from GOP raw scores
    phoneme_evidence = []
    if gop_raw and "phonemes" in gop_raw:
        for ph_data in gop_raw["phonemes"]:
            gap = ph_data.get("gap", 0.0)
            confidence_level = _gap_to_confidence_level(gap)

            # Get error type from word-level phoneme_error_types if available
            ph_error_type = "correct"
            ph_error_conf = 0.0
            phoneme_error_types = word_data.get("phoneme_error_types", [])
            if phoneme_error_types:
                # Match by index (same order)
                idx = gop_raw["phonemes"].index(ph_data)
                if idx < len(phoneme_error_types):
                    ph_error_type = phoneme_error_types[idx].get("error_type", "correct")
                    ph_error_conf = phoneme_error_types[idx].get("error_type_confidence", 0.0)

            phoneme_evidence.append(PhonemeEvidence(
                phoneme=ph_data.get("phoneme", "?"),
                gop_score=ph_data.get("gop_score", -10.0),
                gop_gap=gap,
                max_posterior_phoneme=ph_data.get("max_posterior_phoneme", "?"),
                error_type=ph_error_type,
                error_confidence=ph_error_conf,
                confidence_level=confidence_level,
            ))

    # Overall word confidence level
    overall_confidence = _score_to_confidence_level(word_score, detected_issue)

    return WordEvidence(
        word=word,
        word_score=word_score,
        detected_issue=detected_issue,
        phoneme_evidence=phoneme_evidence,
        expected_phonemes=expected_phonemes,
        substituted_as=substituted_as,
        error_type=error_type,
        error_type_confidence=error_type_confidence,
        confidence_level=overall_confidence,
    )


def format_evidence_for_prompt(evidence: WordEvidence) -> str:
    """
    Format the evidence into a human-readable string for the LLM prompt.
    This is what the LLM sees and must ground its feedback in.
    """
    lines = []
    lines.append(f"WORD: \"{evidence.word}\"")
    lines.append(f"OVERALL SCORE: {evidence.word_score}/100")
    lines.append(f"ISSUE: {evidence.detected_issue}")
    lines.append(f"CONFIDENCE: {evidence.confidence_level}")

    if evidence.error_type != "correct":
        lines.append(f"ERROR TYPE: {evidence.error_type} (confidence: {evidence.error_type_confidence:.0%})")

    if evidence.expected_phonemes:
        lines.append(f"EXPECTED PHONEMES: /{'/'.join(evidence.expected_phonemes)}/")

    if evidence.substituted_as and any(s != e for s, e in zip(evidence.substituted_as, evidence.expected_phonemes)):
        subs = []
        for exp, det in zip(evidence.expected_phonemes, evidence.substituted_as):
            if exp != det:
                subs.append(f"/{exp}/ → /{det}/")
        if subs:
            lines.append(f"SUBSTITUTIONS DETECTED: {', '.join(subs)}")

    if evidence.phoneme_evidence:
        lines.append("\nPHONEME-LEVEL DETAIL:")
        for pe in evidence.phoneme_evidence:
            if pe.gop_gap > 1.5:  # Only show problematic phonemes
                lines.append(
                    f"  /{pe.phoneme}/ — gap={pe.gop_gap:.1f}, "
                    f"model heard /{pe.max_posterior_phoneme}/, "
                    f"error={pe.error_type} [{pe.confidence_level}]"
                )

    return "\n".join(lines)


def _gap_to_confidence_level(gap: float) -> str:
    """Convert GOP gap to a confidence level for the evidence."""
    if gap > 3.0:
        return "High"  # High confidence this is an error
    elif gap > 1.5:
        return "Medium"
    else:
        return "Low"


def _score_to_confidence_level(score: float, issue: str) -> str:
    """Convert word score + issue to an overall confidence level."""
    if issue == "correct":
        return "High"  # High confidence it's correct
    if score < 30:
        return "High"  # High confidence there's an error
    elif score < 60:
        return "Medium"
    else:
        return "Low"  # Low confidence in the error classification
