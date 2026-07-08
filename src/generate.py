# Stage 1: GENERATE. Load gemma base + it, run every prompt through both,
# dump responses to disk. Then this process exits and frees VRAM before judging.
#
#   input : data/prompts.jsonl   {"id","prompt","system"(opt),"lang"(opt),"meta"(opt)}
#   output: results/outputs.jsonl {"id","model","prompt","response","lang","meta"}
import json, sys, argparse
from pathlib import Path
from models import GemmaBase, GemmaIT


def read_jsonl(p):
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", default="data/prompts.jsonl")
    ap.add_argument("--out", default="results/outputs.jsonl")
    ap.add_argument("--max-new-tokens", type=int, default=256)
    ap.add_argument("--models", default="base,it")  # comma list
    args = ap.parse_args()

    prompts = list(read_jsonl(args.prompts))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    which = args.models.split(",")

    with open(args.out, "w") as fout:
        if "base" in which:
            base = GemmaBase()
            for i, ex in enumerate(prompts):
                resp = base.generate(
                    ex["prompt"],
                    system=ex.get("system"),
                    max_new_tokens=args.max_new_tokens,
                )
                fout.write(json.dumps({**ex, "model": "base", "response": resp}) + "\n")
                fout.flush()
                print(f"[base {i+1}/{len(prompts)}] {ex['id']}", file=sys.stderr)
            del base
            import torch, gc; gc.collect(); torch.cuda.empty_cache()

        if "it" in which:
            it = GemmaIT()
            for i, ex in enumerate(prompts):
                resp = it.generate(
                    ex["prompt"],
                    system=ex.get("system", "You are a helpful assistant."),
                    max_new_tokens=args.max_new_tokens,
                )
                fout.write(json.dumps({**ex, "model": "it", "response": resp}) + "\n")
                fout.flush()
                print(f"[it {i+1}/{len(prompts)}] {ex['id']}", file=sys.stderr)

    print(f"Wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
