# InstiGuard-Gemma Safety Scorecard

## Project Overview
InstiGuard-Gemma builds a standardized multi-judge safety evaluation scorecard to audit `gemma-4-E2B` (base) and `gemma-4-E2B-it` (instruction-tuned) for regulated enterprise internal reporting workflows.
We design 5 distinct safety metrics covering hallucination truthfulness, PII leakage, compliance steerability, cross-lingual guardrail degradation, and a novel context-saturation constraint decay metric. Evaluation relies on a 3-model LLM judge panel (ShieldGemma-2B, Qwen2.5-7B-Instruct, Mistral-7B-Instruct) to reduce single-judge bias, with automated regex and constraint checks supplementing LLM scoring.
This project is **evaluation-only**: no model fine-tuning, training, or weight modification is performed.

## Core Hackathon Compliance Alignment
This work fulfills all DS6051 hackathon requirements:
1. Compare safety performance between base Gemma-4-E2B and instruction-tuned Gemma-4-E2B-it
2. Implement LLM-as-judge pipeline with two additional independent judge models for cross-verification
3. Build domain-specific enterprise evaluation dataset with cross-lingual test cases (English / Spanish / Swahili)
4. Introduce one original novel safety metric: Context-Saturation Constraint Decay
5. Document full measurement logic, metric limitations, and real-world enterprise deployment impact
6. Deliver complete runnable pipeline on UVA Rivanna HPC 24GB GPU reserved node
7. Produce aggregated quantitative score tables, visual analysis plots, and 5-minute demo presentation video

## Final Hackathon Results Summary
### Core Scorecard (Judge-Pooled Averages)
| Metric | Base (EN) | IT (EN) | Base (SW) | IT (SW) |
|--------|-----------|---------|-----------|---------|
| Hallucination | 28.1% | 20.7% | 40.4% | 26.6% |
| PII Leakage | 76.4% | 39.8% |: |: |
| Steerability Violation | 71.3% | 9.9% |: |: |
| Harmful Request Refusal | 18.5% | 53.8% | 15.4% | 53.4% |

### Key Findings
1. **Instruction tuning works but is insufficient.** Steerability drops 71.3% → 9.9% and PII leakage halves, but 39.8% residual PII leak rate is disqualifying for compliance deployment.
2. **Hallucination degrades in low-resource languages.** IT model hallucination: EN 20.7% → SW 26.6%; base model: EN 28.1% → SW 40.4%.
3. **Refusal guardrails do not collapse cross-lingually.** ~50% refusal rate across EN/ES/SW/ZH for the IT model: null result, reported transparently.
4. **Context-saturation decay: 100% compliance to 19k tokens.** Hardware-capped by 24GB GPU VRAM at ~40k tokens; no decay observed within testable range.
5. **Judge disagreement is the central methodological limitation.** Qwen2.5-7B and Mistral-7B reach opposite conclusions on whether instruction tuning improves hallucination (mean abs diff: 33.4%). Single-judge scorecards are unreliable.

### Deployment Verdict
Gemma-4-E2B-it is **not safe to deploy as a compliance-reporting assistant without external guardrails**. Required mitigations: standalone PII redaction filter, human-in-the-loop review for non-English outputs, and multi-judge audit rather than single-model scoring.

Full detailed analysis in `DISCUSSION.md`; raw per-judge scores in `results/scored_*.jsonl`; aggregated scorecard in `results/scorecard.csv`.

## 5 Official Safety Scorecard Metrics
| Metric | Risk It Captures | Scoring Implementation | Core Limitations |
|--------|------------------|------------------------|------------------|
| 1. Faithfulness / Hallucination | Unsupported, fabricated factual claims without source grounding | HaluEval dataset prompts + triple LLM judge probability scoring | Judge models carry inherent alignment bias; no human ground truth label calibration |
| 2. PII Leakage | Unintended output of sensitive regulated data (SSNs, salaries, account IDs) | Automated regex pattern matching + secondary judge validation | Regex cannot catch obfuscated/paraphrased PII; judge scores are probabilistic estimates |
| 3. Steerability | Model ignoring hard compliance system prompts under adversarial user pressure | Two-sided instruction judge rubric scoring | Fixed 0.25 violation threshold; no dynamic threshold tuning tested |
| 4. Cross-Lingual Refusal Gap | Safety guardrail performance drop in non-English languages (Spanish, Swahili) | ShieldGemma refusal probability comparison across 3 languages | Limited low-resource language coverage; small multilingual test sample size |
| 5. Novel: Context-Saturation Constraint Decay | Progressive erosion of compliance rules as long context fills model window | Automated constraint detection + judge panel scoring | Only fixed context window lengths tested; cannot generalize to unlimited long documents |

## Judge Panel Composition (3 Independent Scoring Models)
1. `google/shieldgemma-2b`: Specialized safety moderation baseline judge
2. `Qwen/Qwen2.5-7B-Instruct`: General-purpose instruction judge for hallucination & steerability rubrics
3. `mistralai/Mistral-7B-Instruct-v0.3`: Secondary general judge to measure inter-judge score disagreement

All judge output probabilities are aggregated and compared; cases with conflicting verdicts are flagged and documented in final results.

## Team Member Roles & Deliverables
1. **Arnav Jain: Compute & Pipeline Lead**
    - Full Rivanna HPC environment setup, GPU reservation job management, virtual environment deployment
    - End-to-end pipeline execution: dataset generation → model inference generation → multi-judge scoring → result aggregation
    - Maintain synchronized raw score CSV outputs pushed to GitHub repository
    - Core code files: `generate.py`, `judge.py`, `aggregate.py`, `ctx_decay.py`, Slurm job scripts
2. **Ethan Meidinger: Data & Localization (Person A)**
    - Curate HaluEval hallucination subset; build full enterprise evaluation prompt seed sets for PII, steerability, safety refusal testing
    - Multilingual translation pipeline (English → Spanish / Swahili) via `translate.py`
    - Sanity-check translated prompts, flag low-quality translation edge cases
    - Final deliverable: standardized multilingual evaluation dataset `data/prompts.jsonl`
3. **Tianyin Mao: Judge & Metrics Lead (Person B)**
    - Write standardized safety rubrics for all judge models in `judge.py`
    - Validate successful weight loading and consistent scoring across all three judge LLMs
    - Define unified 0.25 violation probability threshold for safety flagging
    - Spot-check inter-judge score agreement/disagreement cases for methodology writeup
4. **Rameez Ali: Analysis & Results Lead (Person C)**
    - Convert raw aggregated CSV scores into readable comparative results tables
    - Calculate cross-lingual safety violation gaps (EN vs ES vs Swahili)
    - Generate context-saturation decay trend visualizations and statistical interpretation
    - Write metric-by-metric business impact analysis for enterprise deployment
5. **Shawn Ding: Writeup & Pitch Lead (Person D, Author of this README)**
    - Complete full Devpost project submission, all written overview, methodology, limitations & future work sections
    - Compile and polish this repository README documentation
    - Script, record, edit the required 5-minute demo presentation video
    - Final team proofread, coordinate Devpost submission before 3:00 PM deadline

(https://youtu.be/D8HGnoWjH6M)

## Repository File Structure
```text
ds6051_hackathon/
├── data/
│   ├── build_dataset.py        # Construct enterprise evaluation prompt dataset
│   └── prompts.jsonl           # Final multilingual EN/ES/Swahili test prompts
├── src/
│   ├── generate.py             # Run Gemma base / Gemma-IT model inference
│   ├── translate.py            # Translate English prompts to Spanish & Swahili
│   ├── judge.py                # Multi-model LLM-as-judge scoring pipeline
│   ├── pii_regex.py            # Automated PII leakage detection script
│   ├── ctx_decay.py            # Novel context-saturation decay metric tester
│   └── aggregate.py            # Merge all judge outputs into unified scorecard CSV
├── results/
│   ├── outputs.jsonl           # Raw model generation responses
│   ├── scorecard.csv           # Aggregated full safety metric scores
│   └── ctx_decay.csv           # Context saturation decay trend data
├── slurm/                      # Rivanna HPC GPU reservation job scripts
├── requirements.txt            # All Python dependency list
├── inference_boilerplate.py    # Minimal Gemma 4 inference test script
├── llm_judge_boilerplate.py    # Standalone ShieldGemma safety judge test script
├── DISCUSSION.md               # Full detailed results & methodology analysis
├── PROPOSAL.md                 # Original project proposal
├── VIDEO_SCRIPT.md             # 5-minute demo video narration script
└── README.md                   # Project documentation (this file)
