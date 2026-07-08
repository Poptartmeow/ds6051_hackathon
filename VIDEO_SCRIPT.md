# InstiGuard-Gemma — ~5-minute video script

Format: talking head + screen-share of `results/figures/*.png` and `results/outputs.jsonl`.
Split lines across team members as you like. Times are cumulative. ~730 words ≈ 5 min.

---

**[0:00–0:35] Hook / problem** — *(show title slide)*
"Imagine an enterprise deploys a small open LLM to write its compliance reports. These reports
touch SSNs, salaries, account numbers, and regulators expect zero fabrication. Is a general-purpose
model actually safe enough for that? We built **InstiGuard-Gemma**, a safety scorecard that answers
that question for Google's Gemma-4-E2B — not by trusting it, but by measuring it."

**[0:35–1:15] What we built** — *(show the scorecard table, DISCUSSION §1)*
"We evaluated two versions, the base model and the instruction-tuned model, across five safety
dimensions: hallucination, PII leakage, steerability, a cross-lingual safety gap, and a novel
context-saturation metric. Every open-ended output is scored by a panel of three judge models, and
we deliberately picked metrics that matter for *this* domain — a fabricated audit source or a leaked
SSN is a regulatory event, not a typo."

**[1:15–2:00] Methodology** — *(show pipeline diagram or run.sbatch)*
"The pipeline generates responses from both Gemma models, dumps them to disk, then loads each judge
one at a time — ShieldGemma for harmful content, and Qwen2.5-7B and Mistral-7B as independent
graders for faithfulness, PII, steerability, and refusal. For the cross-lingual test we translated
the evaluation set into Spanish and low-resource Swahili. Everything ran on a single 24GB GPU on
Rivanna, which — as we'll see — became part of the story."

**[2:00–2:55] Headline result** — *(show `base_vs_it.png`)*
"Here's the core result. Instruction tuning is the safety lever: steerability violations drop from
71% to 10%, and PII leakage is cut in half. But look closer — the instruction-tuned model *still
leaks PII 40% of the time.* Told explicitly 'never disclose an SSN,' two out of five times it does
anyway." *(switch to outputs.jsonl example)* "Here's the base model, given that exact rule, drafting
an IRS notice with the customer's full Social Security number. Instruction tuning is necessary, but
nowhere near sufficient to deploy."

**[2:55–3:30] Cross-lingual** — *(show `crosslingual_hallucination.png`)*
"Cross-lingually, hallucination gets worse as we move to low-resource Swahili — the gradient the
research predicts. But interestingly, refusal of harmful requests did *not* collapse across
languages in our tests. That's an honest null result: the cross-lingual jailbreak effect people
warn about didn't show up on our probe set, and we report that rather than overclaim."

**[3:30–4:20] The judges disagree — our key insight** — *(show `judge_agreement.png`)*
"Now the most important thing we found, and it's about the *method* itself. Our two judges disagree
a lot. On hallucination, their scores differ by 0.33 on average — and they actually reach *opposite
conclusions*. Qwen says instruction tuning makes hallucination worse; Mistral says it makes it
better. If we'd used only one judge, our scorecard would have confidently reported whichever answer
that judge happened to give. LLM-as-judge is a noisy instrument, and for some metrics the choice of
judge flips the deployment recommendation. That's why a panel matters."

**[4:20–4:55] Limitations** — *(show DISCUSSION §3 bullet list)*
"We're explicit about what these numbers can't tell us. The judges are themselves LLMs with the same
failure modes. Regex only catches known PII formats. Steerability measures behavior, not
understanding. And our bonus metric — context-saturation constraint decay — showed no decay up to
19,000 tokens, but at 40,000 the GPU runs out of memory. So that result is a hardware lower bound,
not proof the model never degrades. The architecture literally caps what we can measure."

**[4:55–5:10] Verdict / close** — *(title slide)*
"Our verdict: Gemma-4-E2B-it is not safe to deploy as a compliance assistant without an external
PII filter and a human in the loop for non-English reports. But the deeper lesson is that a safety
scorecard is only as trustworthy as its judges — and being honest about that is the whole point.
Thanks for watching."

---

### Shot list / assets
- Title slide (project name + team)
- `results/figures/base_vs_it.png`
- `results/figures/crosslingual_hallucination.png`
- `results/figures/judge_agreement.png`
- `results/figures/ctx_decay.png` (optional, if time)
- `results/outputs.jsonl` — the base-model SSN-leak line (search `pii-`)
- `DISCUSSION.md` §3 limitations bullets on screen for the closing
