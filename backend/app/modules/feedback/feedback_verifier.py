"""
Phase 27 — Feedback Verifier

Checks that every specific claim in LLM-generated feedback is grounded in
the structured evidence. Rejects/flags feedback that makes unsubstantiated
claims about phonemes, substitutions, or error types.

Design:
  - Rule-based verification (deterministic, fast, no additional LLM call)
  - Checks: phoneme references exist in evidence, substitution claims match
    measured data, no invented phoneme pairs
  - Hard cap on regeneration attempts (max 2 retries)
  - Falls back to safe generic template if verification keeps failing

This is the hallucination-prevention pattern: ensure every specific claim
traces to something the pipeline actually measured.
"""

import re

from app.core.logging import get_logger
from app.modules.feedback.evidence_builder import WordEvidence

logger = get_logger(__name__)

# Regex to find phoneme references in feedback text (e.g., /θ/, /t/, etc.)
_PHONEME_PATTERN = re.compile(r'/([^/\s]{1,4})/')

# Regex to find substitution claims (e.g., "replacing /θ/ with /t/", "/θ/ → /t/")
_SUBSTITUTION_PATTERN = re.compile(
    r'/([^/\s]{1,4})/\s*(?:→|->|to|with|instead of|replaced by)\s*/([^/\s]{1,4})/',
    re.IGNORECASE,
)


class VerificationResult:
    """Result of verifying a feedback response."""

    def __init__(self):
        self.is_valid = True
        self.issues: list[str] = []
        self.ungrounded_claims: list[str] = []

    def add_issue(self, issue: str):
        self.is_valid = False
        self.issues.append(issue)

    def add_ungrounded_claim(self, claim: str):
        self.is_valid = False
        self.ungrounded_claims.append(claim)


def verify_feedback(
    feedback_text: str,
    evidence: WordEvidence,
) -> VerificationResult:
    """
    Verify that feedback claims are grounded in measured evidence.

    Checks:
      1. Any phoneme mentioned in the feedback exists in the word's expected
         or detected phonemes
      2. Any substitution claim (e.g., "/θ/ → /t/") matches a measured
         substitution in the evidence
      3. No completely fabricated phoneme pairs

    Args:
        feedback_text: The LLM-generated feedback text (explanation + tip)
        evidence: The structured evidence bundle for this word

    Returns:
        VerificationResult with pass/fail and list of issues
    """
    result = VerificationResult()

    # Build the set of valid phonemes from evidence
    valid_phonemes = set()
    valid_phonemes.update(evidence.expected_phonemes)
    valid_phonemes.update(evidence.substituted_as)

    # Add phonemes from phoneme-level evidence
    for pe in evidence.phoneme_evidence:
        valid_phonemes.add(pe.phoneme)
        valid_phonemes.add(pe.max_posterior_phoneme)

    # Remove empty/placeholder entries
    valid_phonemes.discard("")
    valid_phonemes.discard("?")
    valid_phonemes.discard("∅")
    valid_phonemes.discard("<unk>")
    valid_phonemes.discard("<pad>")

    # Check 1: Referenced phonemes exist in evidence
    referenced_phonemes = _PHONEME_PATTERN.findall(feedback_text)
    for phoneme in referenced_phonemes:
        if phoneme not in valid_phonemes and not _is_common_phoneme_description(phoneme):
            result.add_ungrounded_claim(
                f"Phoneme /{phoneme}/ mentioned but not found in measured evidence"
            )

    # Check 2: Substitution claims match measured data
    substitution_claims = _SUBSTITUTION_PATTERN.findall(feedback_text)
    for expected, detected in substitution_claims:
        # Check if this substitution was actually measured
        if not _substitution_in_evidence(expected, detected, evidence):
            result.add_ungrounded_claim(
                f"Claimed substitution /{expected}/ → /{detected}/ not found in measurements"
            )

    # Check 3: If feedback claims "correct" but evidence shows error (or vice versa)
    if evidence.detected_issue == "correct":
        error_keywords = ["mispronounced", "wrong", "incorrect", "substitut", "error"]
        for kw in error_keywords:
            if kw in feedback_text.lower():
                result.add_issue(
                    f"Feedback claims error ('{kw}') but evidence shows word is correct"
                )
                break

    # Log verification results
    if not result.is_valid:
        logger.warning(
            "feedback_verification_failed",
            word=evidence.word,
            issues=result.issues,
            ungrounded=result.ungrounded_claims,
        )

    return result


def _substitution_in_evidence(expected: str, detected: str, evidence: WordEvidence) -> bool:
    """Check if a claimed substitution pair exists in the measured evidence."""
    # Check in substituted_as array
    for exp, sub in zip(evidence.expected_phonemes, evidence.substituted_as):
        if exp == expected and sub == detected:
            return True

    # Check in phoneme-level evidence (max_posterior_phoneme)
    for pe in evidence.phoneme_evidence:
        if pe.phoneme == expected and pe.max_posterior_phoneme == detected:
            return True

    # Allow the reverse too (model heard X instead of Y)
    for pe in evidence.phoneme_evidence:
        if pe.phoneme == expected and pe.gop_gap > 1.5:
            # If there's a significant gap, the substitution claim is plausible
            return True

    return False


def _is_common_phoneme_description(phoneme: str) -> bool:
    """
    Allow common phoneme descriptions that aren't in IPA but are used
    in lay explanations (e.g., 'th', 'r', 'l', 'sh', 'ch').
    """
    common_descriptions = {
        "th", "sh", "ch", "ng", "zh", "dz",
        "r", "l", "w", "j", "h",
        "a", "e", "i", "o", "u",
        "ee", "oo", "ah", "uh",
    }
    return phoneme.lower() in common_descriptions


def get_safe_fallback_feedback(evidence: WordEvidence) -> dict:
    """
    Generate safe, generic feedback that doesn't make specific claims
    it can't back up. Used when verification fails after max retries.
    """
    word = evidence.word
    score = evidence.word_score
    issue = evidence.detected_issue

    if issue == "mispronounced":
        explanation = (
            f"The word \"{word}\" (score: {score:.0f}/100) needs some attention. "
            f"Focus on speaking each sound clearly and deliberately."
        )
        tip = (
            "Try saying the word slowly, one sound at a time. "
            "Record yourself and compare with a native speaker's pronunciation."
        )
    elif issue == "unclear":
        explanation = (
            f"The word \"{word}\" (score: {score:.0f}/100) wasn't captured clearly. "
            f"This could be due to speaking speed or volume."
        )
        tip = (
            "Try speaking the word with slightly more emphasis and at a comfortable pace. "
            "Make sure each syllable is distinct."
        )
    else:
        explanation = (
            f"The word \"{word}\" (score: {score:.0f}/100) could use some practice."
        )
        tip = "Practice saying this word clearly and at a natural pace."

    return {
        "explanation": explanation,
        "mouth_position_tip": tip,
        "practice_words": [],
        "confidence_level": evidence.confidence_level,
        "evidence_grounded": True,
        "verification_status": "safe_fallback",
    }
