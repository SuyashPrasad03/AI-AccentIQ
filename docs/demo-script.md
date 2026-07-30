# AccentIQ — 90-Second Demo Script

## Target Audience
AI Engineer / GenAI / ML Engineer hiring managers. This demo shows system breadth and technical depth, not just a pretty UI.

## Order (deliberate: open visual → close technical)

---

### Opening (0–20s): Live Streaming Word-Level Feedback [Phase 30]

**Show**: Dashboard with "Live Practice Mode" active.

**Action**: Click "Start Live Session", speak a sentence ("The three brothers went through the thick forest").

**Highlight**: Words light up green/yellow/red IN REAL TIME as you speak. Show the ~1-2 second latency from speech to score appearing.

**Say**: "Words are scored acoustically in real-time via WebSocket streaming. Each word gets a GOP score from wav2vec2-CTC frame-level posteriors as it's detected."

---

### Middle (20–50s): Evidence-Grounded Feedback + Error Classification [Phase 27 + 25]

**Show**: Click on a word flagged red/yellow (e.g., "three" — /θ/ error).

**Highlight**: The feedback explanation references SPECIFIC measured data: "The /θ/ sound was detected as /t/ (High confidence)..." with a confidence badge.

**Say**: "Every feedback claim is verified against measured acoustic evidence. A LightGBM classifier identifies the specific error type — substitution, deletion, or distortion — and a verifier rejects any LLM-generated claim that isn't backed by pipeline data."

---

### Middle (50–70s): Practice Plan + L1 Adaptation [Phase 31 + 28]

**Show**: Click "Generate Plan" in the Practice Plan section.

**Highlight**: 7-day plan appears targeting the user's ACTUAL weak phonemes (from cross-session error history). Show "Day 1: /θ/" with practice sentences.

**Say**: "An agentic planner aggregates error history across all sessions, clusters recurring weak patterns by frequency times severity, and generates a structured 7-day practice plan from a curated sentence bank. If the user's native language is set, feedback explains WHY the error happens — 'Hindi speakers commonly produce /t/ instead of /θ/ because Hindi lacks the interdental fricative.'"

---

### Close (70–90s): Evaluation Framework + Observability [Phase 26 + 32]

**Show**: Navigate to /admin dashboard. Show the pipeline metrics table.

**Highlight**: Per-stage latency (p50/p95), cost tracking, request counts.

**Say**: "I built a gold-standard evaluation framework — 18 recordings with human ratings, measuring Pearson correlation between system and human scores. The eval runs in CI on every scoring PR. An observability dashboard tracks latency and cost per pipeline stage. If model quality drifts in production, I'd know from the correlation trend before users notice."

---

## Key Technical Points to Emphasize

1. **Not confidence-proxy**: "Previous system used ASR confidence as a pronunciation score — that only tells you WHAT was said, not HOW WELL. GOP scoring uses acoustic posteriors to measure actual phoneme quality."

2. **Trained model, not just API call**: "The error classifier is a LightGBM model I trained on 3,500+ labeled phoneme samples. Honest held-out metrics documented."

3. **Hallucination prevention**: "Every specific claim in AI feedback is verified against measured data before showing to the user. Ungrounded claims are rejected and regenerated."

4. **Production maturity**: "Feature flag for A/B testing scoring engines. Observability dashboard. CI-integrated evaluation. Graceful fallbacks throughout."

---

## Recording Tips
- Use a clean microphone, quiet environment
- Speak naturally (don't over-enunciate for the demo — the system should handle real speech)
- For the streaming demo, pause briefly between words so individual scores are visible
- Keep the admin dashboard populated by running a few recordings through first

---

*Script version: 1.0 | For: AccentIQ v2 portfolio demo*
