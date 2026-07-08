#!/bin/bash
#SBATCH --job-name=hack_pipeline
#SBATCH --account=ds6051-summer
#SBATCH --partition=interactive
#SBATCH --reservation=ds6051-summer-hackathon
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=4:00:00
#SBATCH --output=/scratch/mhq8ka/hackathon/logs/%x_%j.out
#SBATCH --error=/scratch/mhq8ka/hackathon/logs/%x_%j.err

set -e
module load miniforge/26.1.0
source /apps/software/standard/core/miniforge/26.1.0/etc/profile.d/conda.sh
conda deactivate 2>/dev/null || true
conda activate hackathon

export HF_HOME="/scratch/$USER/hf_cache"
export TRANSFORMERS_CACHE="/scratch/$USER/hf_cache/transformers"
mkdir -p "$HF_HOME" /scratch/$USER/hackathon/logs

cd /scratch/$USER/hackathon/ds6051_hackathon

# --- Stage 0: build the multilingual prompt set (HaluEval en/es/sw + PII/steer/refuse
# probes). Reads the local qa_data_250_*.json files, no GPU needed.
python data/build_dataset.py --out data/prompts.jsonl

# --- Stage 0b: NLLB-translate the EN 'refused' probes into ES/SW and append them.
# Run ONCE — re-running this line on an already-translated prompts.jsonl duplicates rows.
python src/translate.py --in data/prompts.jsonl --out data/prompts.jsonl

# --- Stage 1: generate (loads gemma base+it, dumps outputs, frees VRAM on exit)
python src/generate.py --prompts data/prompts.jsonl --out results/outputs.jsonl

# --- Stage 2: judges (one process each = one model in VRAM at a time)
python src/judge.py --in results/outputs.jsonl --judge shield
python src/judge.py --in results/outputs.jsonl --judge instruct \
    --model Qwen/Qwen2.5-7B-Instruct   --rubric hallucination
python src/judge.py --in results/outputs.jsonl --judge instruct \
    --model mistralai/Mistral-7B-Instruct-v0.3 --rubric hallucination

# --- Stage 3: aggregate into the results table
python src/aggregate.py --glob 'results/scored_*.jsonl' --out results/scorecard
