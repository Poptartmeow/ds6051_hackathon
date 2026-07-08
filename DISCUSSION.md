# InstiGuard-Gemma: Safety Evaluation Scorecard — Discussion

**Domain / use-case:** an enterprise **data-governance / regulated-reporting assistant**. We
treat the general-purpose Gemma-4-E2B models as if they were deployed to draft and summarize
compliance reports over sensitive corporate and customer data, and ask a single question:
*is this model safe enough to deploy here?* This is an **evaluation**, not a training exercise —
we do not fine-tune the model.

We score the **base** (`gemma-4-E2B`) and **instruction-tuned** (`gemma-4-E2B-it`) variants across
five safety dimensions, using a **three-model judge panel** (ShieldGemma-2B + Qwen2.5-7B-Instruct
+ Mistral-7B-Instruct) plus automated checks, and stress-test the model across languages.

---

## 1. The scorecard: what we measure, why, and how

| # | Metric | Why it matters for regulated reporting | How measured | Key limitation |
|---|---|---|---|---|
| 1 | **Faithfulness / hallucination** | A fabricated figure or entity in a compliance report is a regulatory liability | HaluEval context+question, LLM-judge checks answer is grounded | Judge is itself an LLM and unreliable (see §3) |
| 2 | **PII leakage** | Emitting SSNs / account numbers / salaries violates GDPR/HIPAA/SOX | Automated regex + LLM-judge on seeded-PII docs with a "never disclose" rule | Regex catches known formats only; judge misses novel PII |
| 3 | **Steerability** | The system prompt must reliably constrain behavior ("never disclose salaries") | LLM-judge: did the response violate the imposed rule? | Measures compliance, not whether the model "understood" the rule |
| 4 | **Cross-lingual safety gap** | Global enterprises process multilingual data; guardrails may not transfer | Same items in EN/ES/SW (hallucination) + refusal probes in EN/ES/ZH/SW | Google/NLLB translation adds noise; conflates language ability with safety |
| 5 | **[BONUS] Context-saturation constraint decay** | Small models have compressed context windows; do they drop a hard rule as context grows? | Automated: grow retrieved context, check a mandatory token survives | Testable only to ~19k tokens before the 24GB GPU OOMs |

We also report ShieldGemma's native harm categories (dangerous content, harassment, hate speech)
as a floor check that the model is not emitting overtly toxic content in this domain.

---

## 2. Results

Pooled scorecard (mean over the judge panel; higher = worse, except `refused` where higher = safer):

| metric | base/en | base/es | base/sw | it/en | it/es | it/sw |
|---|---|---|---|---|---|---|
| hallucination | 0.281 | 0.327 | 0.404 | 0.207 | 0.196 | 0.266 |
| pii_leak | **0.764** | — | — | **0.398** | — | — |
| steerability_violation | **0.713** | — | — | **0.099** | — | — |
| refused (harmful) | 0.185 | 0.241 | 0.154 | 0.538 | 0.498 | 0.534 |
| shield.dangerous | 0.004 | 0.003 | 0.014 | 0.006 | 0.007 | 0.007 |

*(refused also EN/ZH: base 0.185/0.131, it 0.538/0.506. ShieldGemma harassment/hate ≈ 0.00–0.01 everywhere.)*

**Finding 1 — Instruction tuning is the safety lever, but not a fix.**
Moving from base to instruction-tuned collapses steerability violations **0.713 → 0.099** and
halves PII leakage **0.764 → 0.398**. But a **40% PII-leak rate on the deployed (-it) model is
disqualifying** for a compliance assistant: 2 out of 5 times it emits data it was explicitly told
to redact. See `results/figures/base_vs_it.png`. In `results/outputs.jsonl` the base model, told
"never include SSNs," drafts an IRS notice containing the full SSN verbatim.

**Finding 2 — Hallucination worsens toward low-resource languages.**
Instruction-tuned hallucination rises **English 0.207 → Swahili 0.266** (base 0.281 → 0.404), the
resource gradient the literature predicts. See `results/figures/crosslingual_hallucination.png`.

**Finding 3 — Refusal does *not* collapse cross-lingually.**
The -it model refuses harmful/non-compliant requests at ~0.50 across EN/ES/SW/ZH — no dramatic
low-resource guardrail failure on our probe set. An honest null result: the widely-cited
cross-lingual jailbreak effect did not reproduce here (small probe set, n=8/language).

**Finding 4 (bonus) — No constraint decay within testable range.**
The -it model holds a mandatory-token constraint at 100% compliance from 1k to **19k tokens** of
context; at ~40k tokens the 24GB GPU OOMs, so we cannot probe further. See
`results/figures/ctx_decay.png`. The measurement is capped by hardware, not by observing decay.

---

## 3. Judge panel and its limitations (the honest core)

We ran two independent instruct judges (Qwen2.5-7B, Mistral-7B) on every open-ended metric and
compared them. **They disagree substantially — and on hallucination they disagree on direction.**

| metric | Qwen mean | Mistral mean | mean abs diff |
|---|---|---|---|
| hallucination | 0.228 | 0.332 | **0.334** |
| pii_leak | 0.722 | 0.522 | 0.287 |
| steerability_violation | 0.397 | 0.415 | 0.207 |
| refused | 0.251 | 0.446 | 0.211 |

The clearest warning: on **hallucination, base vs instruction-tuned**, the two judges reach
**opposite conclusions** —

| judge | base/en | it/en | verdict |
|---|---|---|---|
| Qwen2.5-7B | 0.152 | 0.247 | instruction-tuned is *worse* |
| Mistral-7B | 0.409 | 0.167 | instruction-tuned is *better* |

The pooled number (base 0.281 > it 0.207) is an artifact of averaging two judges who disagree.
**This is the central limitation of the whole scorecard:** LLM-as-judge is a noisy instrument, and
for a metric like hallucination the choice of judge can flip the deployment recommendation. A
single-judge scorecard would have silently reported whichever answer that judge happened to give.
See `results/figures/judge_agreement.png`.

### What the measurements cannot tell us (given current LLM architecture)
- **The judges are LLMs with the same failure modes as the model under test** — they hallucinate
  their own verdicts, and small (7B) judges are especially noisy (§3). Numbers are *relative
  signals*, not ground truth.
- **PII regex catches only known formats** (SSN, card, routing); a leaked name+context pair it
  cannot see. Automated + judge together still under-count.
- **Steerability measures behavior, not understanding** — we observe whether the rule was honored,
  not whether the model represents the constraint; the same prompt phrased differently may flip it.
- **Cross-lingual conflates translation noise, language competence, and safety.** A higher Swahili
  hallucination rate could be worse grounding *or* worse Swahili, not a guardrail failure.
- **The bonus metric is hardware-capped:** "no decay to 19k tokens" is a lower bound set by 24GB of
  VRAM, not evidence that decay never happens.
- **Small sample on the safety probes** (PII/steerability n=5, refusal n=8/lang): directional, not
  statistically tight.

---

## 4. Deployment verdict

Gemma-4-E2B-it is **not safe to deploy as an enterprise compliance-reporting assistant without
guardrails**: it leaks PII ~40% of the time and hallucinates more in low-resource languages.
Instruction tuning is necessary (it fixes steerability and halves leakage) but not sufficient. Any
deployment would need an external PII-redaction filter and a human-in-the-loop for non-English
reporting. And our own scorecard's reliability is bounded by the judges — a lesson as important as
any single number.

---

*Reproduce:* `sbatch slurm/run.sbatch` (full pipeline) → `python src/analyze.py` (tables + figures).
Raw per-judge scores in `results/scored_*.jsonl`; figures in `results/figures/`.
