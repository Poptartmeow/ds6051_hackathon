#!/bin/bash
#SBATCH --job-name=hack_pipeline
#SBATCH --account=ds6051-summer
#SBATCH --partition=interactive
#SBATCH --reservation=ds6051-summer-hackathon
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=4:00:00
#SBATCH --output=/scratch/%u/hackathon/logs/%x_%j.out
#SBATCH --error=/scratch/%u/hackathon/logs/%x_%j.out

set -euo pipefail
module load miniforge/26.1.0
source /apps/software/standard/core/miniforge/26.1.0/etc/profile.d/conda.sh
conda deactivate 2>/dev/null || true
conda activate hackathon

export HF_HOME="/scratch/$USER/hf_cache"
export TRANSFORMERS_CACHE="$HF_HOME/transformers"
mkdir -p "$HF_HOME" /scratch/$USER/hackathon/logs
# Surface the token from the default cache so gated loads work under HF_HOME on scratch.
if [ -z "${HF_TOKEN:-}" ] && [ -f "$HOME/.cache/huggingface/token" ]; then
  export HF_TOKEN="$(cat "$HOME/.cache/huggingface/token")"
fi

cd /scratch/$USER/hackathon/ds6051_hackathon

# Stage 0: build multilingual prompt set (halluc EN/ES/SW + PII/steer/refuse probes)
python data/build_dataset.py --out data/prompts.jsonl
# Stage 0b: NLLB-translate the EN refusal probes into ES/SW (run once per build)
python src/translate.py --in data/prompts.jsonl --out data/prompts.jsonl

# Stage 1: generate (gemma base + it), dump outputs, free VRAM on exit
python src/generate.py --prompts data/prompts.jsonl --out results/outputs.jsonl

# Stage 2: judge panel. ShieldGemma harm scores, then Qwen + Mistral over each rubric.
python src/judge.py --in results/outputs.jsonl --judge shield
for MODEL in "Qwen/Qwen2.5-7B-Instruct" "mistralai/Mistral-7B-Instruct-v0.3"; do
  for RUBRIC in hallucination pii_leak steerability_violation refused; do
    python src/judge.py --in results/outputs.jsonl --judge instruct \
        --model "$MODEL" --rubric "$RUBRIC"
  done
done

# Stage 2b: automated PII regex + bonus context-saturation constraint decay
python src/pii_regex.py --in results/outputs.jsonl --out results/scored_pii_regex.jsonl
python src/ctx_decay.py --out results/ctx_decay.csv --sections 0,25,100,400,1000,2000

# Stage 3: aggregate everything into the scorecard table
python src/aggregate.py --glob 'results/scored_*.jsonl' --out results/scorecard
echo "######## FULL SCORECARD RUN COMPLETE ########"
cat results/scorecard.md
