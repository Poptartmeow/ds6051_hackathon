# InstiGuard-Gemma: A Safety-Evaluation Scorecard for Small LLMs in Regulated Enterprise Reporting

**DS6051 Hackathon · July 8, 2026 · Submission due 3:00 PM on Devpost**

## Executive summary

Over one six-hour session, our team of 5 builds a deployment-readiness safety scorecard for small open-weight LLMs in a regulated enterprise reporting domain. We act as if the general-purpose gemma-4-E2B models were the candidate models for an enterprise compliance assistant, and ask the question a real deployer must answer: **is this model safe enough to ship — and how would we know?** We do not train, fine-tune, or improve the model; we measure it. Five metrics run against both the base and instruction-tuned models, scored by a three-model judge panel, with a cross-lingual stress test (English / Spanish / Swahili) and one novel automated metric.

## What we discovered in the boilerplate (design change)

The provided judge scaffold is **ShieldGemma — a harm classifier, not a general judge.** It scores only dangerous-content, harassment, and hate speech; it cannot judge hallucination, PII, or formatting. So the judge panel becomes:

| Judge | Type | Scores |
|---|---|---|
| ShieldGemma-2B (provided) | Native harm classifier | Harm-category probability |
| Qwen2.5-7B-Instruct | General instruct judge (Yes/No logit trick) | Hallucination, PII, steerability, refusal |
| Mistral-7B-Instruct-v0.3 | Same rubrics, independent second opinion | Inter-judge agreement |

Running two independent instruct judges on identical rubrics turns "we used an LLM judge" into "we measured whether LLM judges even agree" — we report where they disagree.

## The scorecard

| # | Metric | What it catches | How it's scored | Known limitation |
|---|---|---|---|---|
| 1 | Faithfulness / hallucination | Unsupported claims vs. source context | HaluEval QA subset + instruct judges | 7B judges can hallucinate their own verdicts; we report inter-judge agreement |
| 2 | PII leakage | Emitting SSNs, accounts, salaries it was told to redact | Seeded synthetic records + no-leak rule; deterministic regex **and** judge (belt + suspenders) | Regex catches formats, not paraphrased leaks; judge catches paraphrase but adds noise |
| 3 | Steerability | Violating a compliance system rule under user pressure | Rule + tempting request; instruct judge scores violation | Small hand-written probe set; violation can be a judgment call |
| 4 | Cross-lingual refusal gap | Guardrails weakening in ES / Swahili vs. English | Harmful enterprise probes translated by NLLB-200; ShieldGemma + refusal judge, per language | MT adds noise; judges are English-centric — scoring Swahili is itself a small-model limitation we document |
| 5 | **Context-saturation constraint decay (novel)** | Silently dropping a hard rule as context fills the window | One verbatim-checkable rule, context padded in steps (0→200 sections); exact-match check — fully automated, no judge | Synthetic filler; one rule, one model — a probe, not a benchmark |

Metrics 1–3 compare **base vs. instruction-tuned** (the base model receives rules prepended to its prompt, since it has no system turn). Metric 4 runs on the -it model across EN/ES/SW. Metric 5 directly targets the transformer context-window limitation the rubric asks us to reflect on. Higher scores are worse for all metrics except refusal rate (metric 4), where refusing a harmful request is the safe outcome — the results table labels this explicitly.

## Architecture: 3-stage pipeline (never exceeds the 24GB card)

```
Stage 1  generate.py   load gemma base + it -> run all prompts -> dump JSONL -> exit (frees VRAM)
Stage 2  judge.py      load ONE judge at a time -> score dumped outputs -> scored_*.jsonl
         pii_regex.py  deterministic PII scoring (no GPU)
Stage 3  aggregate.py  join scored files -> per-model, per-language scorecard (CSV + Markdown)
Bonus    ctx_decay.py  automated constraint-decay curve (own GPU pass)
```

- **Infrastructure:** Rivanna, 1×24GB GPU — `--account=ds6051-summer --partition=interactive --reservation=ds6051-summer-hackathon --gres=gpu:1`. HF cache on `/scratch`. **ShieldGemma-2b is license-gated on HF — the account running the pipeline must accept it in advance** (gemma-4 base/it, Qwen, Mistral, NLLB are all ungated — verified July 8).
- **Dataset:** HaluEval QA subset (committed to repo — no download dependency) + synthetic PII / steerability / refusal probes; refusal probes translated to Spanish and Swahili by NLLB-200-distilled-600M.
- **MVP-first execution:** English metrics 1–3 with one judge → judge panel → cross-lingual → bonus metric. Any tier not producing numbers by 1:30 PM is cut and documented as designed-but-cut.

## Run order (Arnav drives)

```bash
python data/build_dataset.py --out data/prompts.jsonl
python src/translate.py --in data/prompts.jsonl --out data/prompts.jsonl   # run ONCE (re-running duplicates rows)
python src/generate.py --prompts data/prompts.jsonl --out results/outputs.jsonl

python src/judge.py --judge shield
python src/judge.py --judge instruct --model Qwen/Qwen2.5-7B-Instruct           --rubric hallucination
python src/judge.py --judge instruct --model Qwen/Qwen2.5-7B-Instruct           --rubric steerability_violation
python src/judge.py --judge instruct --model Qwen/Qwen2.5-7B-Instruct           --rubric refused
python src/judge.py --judge instruct --model Qwen/Qwen2.5-7B-Instruct           --rubric pii_leak
python src/judge.py --judge instruct --model mistralai/Mistral-7B-Instruct-v0.3 --rubric hallucination
python src/judge.py --judge instruct --model mistralai/Mistral-7B-Instruct-v0.3 --rubric steerability_violation
python src/judge.py --judge instruct --model mistralai/Mistral-7B-Instruct-v0.3 --rubric refused
python src/pii_regex.py

python src/ctx_decay.py --out results/ctx_decay.csv
python src/aggregate.py
```

> **Note (B + Arnav):** judge.py must filter rows to the rubric's own metric (`meta.metric`) before scoring, and generate.py must prepend the `system` rule for the base model — both are open fixes; see team chat.

## Team roles

| Person | Role | Owns | Deliverable |
|---|---|---|---|
| Arnav | Compute & Pipeline | All Rivanna work: env, GPU jobs, full run order; HF access; sync `results/` to repo. Files: `generate.py`, `judge.py`, `aggregate.py`, `ctx_decay.py`, `slurm/` | Working pipeline + raw scorecard outputs on GitHub |
| A | Data & Localization | HaluEval subset from `qa_data.json`; expand + sanity-check PII / steerability / refusal seed sets; verify ES + SW translations read correctly | Final multilingual dataset (`data/prompts.jsonl`) |
| B | Judge & Metrics | Judge rubrics in `judge.py`; validate both extra judges; set violation thresholds; spot-check judge agreement | Metric definitions + judge methodology writeup |
| C | Analysis & Results | Raw outputs → results table; cross-lingual gap (EN/ES/SW); context-decay curve plot; per-metric interpretation for deployment | Results table + interpretation |
| D | Writeup & Pitch | Overview, methodology + limitations discussion, README, ~5-min video, Devpost submission | Complete Devpost submission |

Work flows A + B → Arnav (datasets + rubrics) → Arnav computes and pushes raw results → C + D consume. Only Arnav touches Rivanna.

## Timeline to 3:00 PM

| By | Milestone |
|---|---|
| 10:30 | Dataset final (A) + judges validated (B); Arnav's smoke test passes |
| 12:00 | Full generate + all judges run; raw scorecard.csv pushed |
| 1:00 | Cross-lingual + ctx-decay done |
| 2:00 | Results table + plots + interpretation (C) |
| 2:45 | Writeup + video done (D) |
| 3:00 | Devpost submitted, with buffer |

## Grading map (80 pts)

| Criterion | Pts | Won by |
|---|---|---|
| Technical implementation | 30 | Arnav + B |
| Innovation & creativity | 20 | Novel metric #5 + judge-panel comparison |
| Problem-solving & impact | 20 | C + D — the limitations discussion |
| Presentation / pitch | 10 | D |

Peer feedback (PPCO on 2 groups) due EOD July 10 — everyone.

## Deliverables (Devpost)

Full scorecard with justifications and limitations · GitHub repo with staged run instructions · Results table (per-model, per-language) · Written discussion of what the measurements mean for enterprise deployment and what they *cannot* tell us given current transformer architecture · ~5-minute video.

Repo: github.com/Poptartmeow/ds6051_hackathon — everyone works off main; pull before you push.
