# Stage 3: AGGREGATE. Join all scored_*.jsonl into one results table
# (per-model, per-metric means) and emit CSV + Markdown for the Devpost writeup.
import json, glob, argparse
from collections import defaultdict
from pathlib import Path


def read_jsonl(p):
    with open(p) as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="results/scored_*.jsonl")
    ap.add_argument("--out", default="results/scorecard")
    args = ap.parse_args()

    # metric_name -> model -> list of scores (optionally split by lang)
    agg = defaultdict(lambda: defaultdict(list))
    for path in glob.glob(args.glob):
        for r in read_jsonl(path):
            model = r.get("model", "?")
            lang = r.get("lang", "en")
            key_model = f"{model}/{lang}"
            for k, v in r.items():
                if k == "shield" and isinstance(v, dict):
                    for cat, p in v.items():
                        agg[f"shield.{cat}"][key_model].append(p)
                elif k.endswith("__pYes"):
                    agg[k[:-6]][key_model].append(v)

    models = sorted({m for d in agg.values() for m in d})
    metrics = sorted(agg)

    # CSV
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out + ".csv", "w") as f:
        f.write("metric," + ",".join(models) + "\n")
        for met in metrics:
            cells = []
            for m in models:
                vals = agg[met][m]
                cells.append(f"{sum(vals)/len(vals):.4f}" if vals else "")
            f.write(met + "," + ",".join(cells) + "\n")

    # Markdown
    with open(args.out + ".md", "w") as f:
        f.write("| metric | " + " | ".join(models) + " |\n")
        f.write("|" + "---|" * (len(models) + 1) + "\n")
        for met in metrics:
            cells = []
            for m in models:
                vals = agg[met][m]
                cells.append(f"{sum(vals)/len(vals):.3f}" if vals else "—")
            f.write(f"| {met} | " + " | ".join(cells) + " |\n")

    print(f"Wrote {args.out}.csv and {args.out}.md")
    print(open(args.out + ".md").read())


if __name__ == "__main__":
    main()
