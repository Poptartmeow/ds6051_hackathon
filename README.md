# Inspiration

Every enterprise wants to deploy small, self-hostable LLMs — they're cheap, private, and fast. But "is this model safe enough for regulated work?" usually gets answered with a demo, not a measurement. Our DS6051 safety lectures kept returning to one theme: you can't manage what you can't measure. So instead of building another chatbot, we built the thing a real compliance team would need first: a scorecard that turns "seems fine" into numbers.

# What it does

InstiGuard-Gemma is a deployment-readiness safety scorecard for `gemma-4-E2B` and its instruction-tuned variant, treating them as candidate models for an enterprise compliance-reporting assistant. It measures five things: hallucination rate (on HaluEval ground-truth pairs), PII leakage (seeded synthetic records the model is told to redact), steerability (system rules under user pressure), a cross-lingual refusal gap (harmful enterprise requests in English, Spanish, Swahili, and Chinese), and a novel automated metric we call **context-saturation constraint decay** — whether the model silently drops a hard rule as its context window fills. Every open-ended output is scored by a three-model judge panel, and we explicitly report where the judges disagree.

# How we built it

A three-stage pipeline on a single 24GB GPU on UVA's Rivanna cluster: generate everything and dump to disk, then load one judge at a time to score the dumps, then aggregate into the scorecard — so no two large models ever share VRAM. We sampled 250 HaluEval QA entries and hand-built the PII, steerability, and refusal probe sets. Refusal probes were machine-translated with NLLB-200. The judge panel is ShieldGemma-2B for harm categories plus Qwen2.5-7B and Mistral-7B as independent rubric judges, using a Yes/No logit trick that reads the probability directly instead of parsing free text. The constraint-decay metric needs no judge at all — just an exact-match check as we pad the context from 0 to ~19,000 filler tokens.

# Results & Key Findings

## Headline Verdict

Our three-judge panel scorecard delivers a clear deployment verdict: **Gemma-4-E2B-it is NOT safe to deploy as an enterprise compliance-reporting assistant without additional guardrails**. Instruction tuning fixes steerability and halves PII leakage, but a 40% PII leak rate on the deployed model remains disqualifying for regulated work.

## Core Scorecard (Judge-Panel Averages)

Higher = worse violation probability, except `refused` where higher = safer.

| Metric | Base Model (English) | Instruction-Tuned (English) | Base (Swahili) | IT (Swahili) |
|--------|---------------------|----------------------------|----------------|--------------|
| Hallucination Rate | 28.1% | 20.7% | 40.4% | 26.6% |
| PII Leakage | **76.4%** | **39.8%** | — | — |
| Steerability Violation | **71.3%** | **9.9%** | — | — |
| Harmful Request Refusal Rate | 18.5% | 53.8% | 15.4% | 53.4% |
| ShieldGemma — Dangerous Content | 0.4% | 0.6% | 1.4% | 0.7% |
| ShieldGemma — Harassment | 0.1% | 0.0% | 0.2% | 0.0% |
| ShieldGemma — Hate Speech | 0.2% | 0.1% | 1.2% | 0.1% |

### Finding 1 — Instruction tuning is the safety lever, but not a fix

Moving from base to instruction-tuned collapses steerability violations from **71.3% → 9.9%** and halves PII leakage from **76.4% → 39.8%**. But a 40% PII-leak rate on the deployed (-it) model is disqualifying for a compliance assistant: told explicitly "never include SSNs," the model still emits the full Social Security number verbatim 2 out of 5 times. The base model, given the same rule, drafts an IRS notice containing the customer's full SSN.

### Finding 2 — Hallucination worsens toward low-resource languages

Instruction-tuned hallucination rises from **English 20.7% → Swahili 26.6%** (base model: 28.1% → 40.4%), following the resource gradient predicted by existing literature. Cross-lingual safety degradation is real and measurable for factual grounding tasks.

### Finding 3 — Refusal does NOT collapse cross-lingually (honest null result)

The -it model refuses harmful/non-compliant requests at ~50% across English, Spanish, Swahili, and Chinese — no dramatic low-resource guardrail failure on our probe set. The widely-cited cross-lingual jailbreak effect did not reproduce here (small probe set, n=8 per language), and we report this null result rather than overclaim.

### Finding 4 — Novel Context-Saturation Constraint Decay: no decay within testable range

The -it model holds a mandatory-token constraint at **100% compliance from 1,000 to 19,000 tokens** of context. At ~40,000 tokens the 24GB GPU runs out of memory, so we cannot probe further. This result is a hardware-capped lower bound, not evidence that decay never happens — the GPU architecture itself limits what we can measure.

### Finding 5 — The judges disagree, and that's the most important result

Our two independent instruct judges (Qwen2.5-7B, Mistral-7B) disagree substantially on every metric. On hallucination, they reach **opposite conclusions** about whether instruction tuning helps:

| Metric | Qwen Mean | Mistral Mean | Mean Absolute Difference |
|--------|-----------|--------------|--------------------------|
| Hallucination | 22.8% | 33.2% | **33.4%** |
| PII Leak | 72.2% | 52.2% | 28.7% |
| Steerability Violation | 39.7% | 41.5% | 20.7% |
| Refusal Rate | 25.1% | 44.6% | 21.1% |

Qwen reports that instruction tuning makes hallucination *worse*; Mistral reports it makes hallucination *better*. The pooled average is an artifact of averaging two judges who disagree in opposite directions. **This is the central limitation of the entire scorecard:** LLM-as-judge is a noisy instrument, and for hallucination the choice of judge can flip the deployment recommendation. A single-judge scorecard would have silently reported whichever answer that one judge happened to give.

## Final Deployment Verdict

Gemma-4-E2B-it is **not safe to deploy as an enterprise compliance-reporting assistant without additional guardrails**. Any production deployment would need:
- An external PII-redaction filter layer (the model cannot reliably self-redact)
- Human-in-the-loop review for all non-English reporting outputs
- Independent multi-judge audit, not a single safety classifier

# Challenges we ran into

The provided judge scaffold turned out to be a harm classifier, not a general judge — ShieldGemma can flag dangerous content but can't score hallucination or formatting, which forced us to redesign our judge panel on the fly and add two independent instruct judges. We also caught two subtle evaluation bugs before they poisoned our numbers: our judges were initially scoring every row with every rubric (inflating hallucination rates with rows that were never hallucination tests), and our base model was being graded on rules it had never been shown, since it has no system turn. On the infrastructure side, Rivanna SSH idle timeouts repeatedly killed our environment, forcing multiple venv rebuilds, and HuggingFace gated-model 403 errors required re-authentication after every session reset. Our context-decay metric also hit a hard hardware wall: at ~40,000 tokens the 24GB GPU OOMs, so we can only report a lower bound, not a true decay curve.

# Accomplishments that we're proud of

A complete, reproducible scorecard with real numbers across every dimension:
- Steerability violations drop from **71.3% → 9.9%** after instruction tuning
- PII leakage is cut in half (76.4% → 39.8%) — but the 40% residual leak rate is still disqualifying for compliance work
- Hallucination rises from **20.7% in English to 26.6% in Swahili** for the instruction-tuned model, confirming the low-resource safety gradient
- Refusal rate stays flat at ~50% across all four tested languages — an honest null result we report instead of hiding
- Our constraint-decay test shows 100% compliance up to 19,000 tokens (hardware-capped)
- Most importantly: our two instruct judges disagree on **hallucination direction** — Qwen says IT is worse, Mistral says IT is better. We report this disagreement openly rather than averaging it away.

# What we learned

Evaluation is harder than generation. Most of our real work went into making the measurements trustworthy — filtering rubrics, validating judges on known cases, keeping polarity straight — not into running models. And small judges have the same architectural ceilings as the models they grade: on hallucination, the two 7B judges give opposite deployment verdicts, which means any single-judge safety scorecard is fundamentally unreliable. The deeper lesson isn't about Gemma — it's about LLM-as-judge methodology itself.

# What's next for InstiGuard-Gemma

Scaling the judge panel independently of the target model to separate "the metric is bad" from "the judge is too small"; expanding constraint decay from one rule to a full battery of compliance constraints; testing whether the cross-lingual hallucination gap closes with in-language system prompts rather than English ones; and adding an external PII-redaction mitigation layer to test whether the 40% leak rate can be brought down to deployable levels.
