"""
Prompt templates for practice sentence generation.
"""

SYSTEM_PROMPT = """You are an English pronunciation practice generator. Generate short, natural-sounding English sentences that target specific sounds the learner needs to practice.

RULES:
- Each sentence should be 5-10 words long.
- Each sentence must heavily feature the target sound(s).
- Use common, everyday vocabulary (not obscure words).
- Make sentences interesting and varied (not repetitive patterns).
- Output ONLY valid JSON matching this schema:

{
  "sentences": [
    {"text": "sentence here", "targets": ["target_phoneme"]}
  ]
}

Generate exactly one sentence per target phoneme provided."""


def build_practice_prompt(weak_phonemes: list[str]) -> str:
    """Build the user prompt for practice sentence generation."""
    phoneme_descriptions = {
        "θ": "TH as in 'think' (voiceless dental fricative)",
        "ð": "TH as in 'this' (voiced dental fricative)",
        "r": "R as in 'red' (English approximant R)",
        "l": "L as in 'love' (lateral approximant)",
        "v": "V as in 'very' (voiced labiodental fricative)",
        "w": "W as in 'water' (labial-velar approximant)",
        "ŋ": "NG as in 'sing' (velar nasal)",
        "ʃ": "SH as in 'ship' (voiceless postalveolar fricative)",
        "ʒ": "ZH as in 'measure' (voiced postalveolar fricative)",
        "dʒ": "J as in 'judge' (voiced postalveolar affricate)",
        "tʃ": "CH as in 'church' (voiceless postalveolar affricate)",
        "z": "Z as in 'zoo' (voiced alveolar fricative)",
        "æ": "short A as in 'cat'",
        "ɪ": "short I as in 'bit'",
        "ʌ": "short U as in 'cup'",
    }

    lines = ["Generate practice sentences for these target sounds:\n"]
    for ph in weak_phonemes:
        desc = phoneme_descriptions.get(ph, f"the sound /{ph}/")
        lines.append(f"- /{ph}/ — {desc}")

    lines.append(f"\nGenerate exactly {len(weak_phonemes)} sentences, one per target sound.")
    return "\n".join(lines)


# ── Fallback sentences (used when LLM is unavailable) ─────────────────────────

_FALLBACK_SENTENCES = {
    "θ": {"text": "Think three thoughts through and through.", "targets": ["θ"]},
    "ð": {"text": "This is the other brother.", "targets": ["ð"]},
    "r": {"text": "The red robin ran rapidly around.", "targets": ["r"]},
    "l": {"text": "Lucy loved the lovely little lake.", "targets": ["l"]},
    "v": {"text": "Very vivid violet valleys vanished.", "targets": ["v"]},
    "w": {"text": "We went walking in warm weather.", "targets": ["w"]},
    "ŋ": {"text": "Singing songs brings strong feelings.", "targets": ["ŋ"]},
    "ʃ": {"text": "She showed the shiny shoes to Sharon.", "targets": ["ʃ"]},
    "ʒ": {"text": "The usual measure of pleasure.", "targets": ["ʒ"]},
    "z": {"text": "Zoe zipped through the busy zoo.", "targets": ["z"]},
    "æ": {"text": "The happy cat sat on a flat mat.", "targets": ["æ"]},
    "ɪ": {"text": "His sister knitted a little mitten.", "targets": ["ɪ"]},
}


def get_fallback_sentences(weak_phonemes: list[str]) -> list[dict]:
    """Static fallback when LLM is unavailable."""
    default = {"text": "Practice speaking clearly and slowly.", "targets": []}
    return [_FALLBACK_SENTENCES.get(ph, default) for ph in weak_phonemes]
