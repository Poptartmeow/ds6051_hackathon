# Person C analysis: per-judge breakdown, judge agreement, and all figures,
# computed from the real results/scored_*.jsonl. Run:  python src/analyze.py
import json, csv, glob, statistics
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RES = Path("results")
FIG = RES / "figures"; FIG.mkdir(parents=True, exist_ok=True)
JUDGES = ["Qwen2.5-7B-Instruct", "Mistral-7B-Instruct-v0.3"]
RUBRICS = ["hallucination", "pii_leak", "steerability_violation", "refused"]
LANGS = ["en", "es", "sw", "zh"]
LANG_NAME = {"en": "English", "es": "Spanish", "sw": "Swahili(low-res)", "zh": "Mandarin"}


def load(path):
    p = RES / path
    return [json.loads(l) for l in open(p, encoding="utf-8")] if p.exists() else []


def mean(xs):
    return sum(xs) / len(xs) if xs else None


# ---- 1. Per-judge means: judge -> rubric -> (model,lang) -> mean pYes ----
def per_judge():
    out = {}
    for j in JUDGES:
        out[j] = {}
        for r in RUBRICS:
            rows = load(f"scored_{j}_{r}.jsonl")
            cells = {}
            key = f"{r}__pYes"
            for row in rows:
                if key not in row:
                    continue
                k = (row.get("model", "?"), row.get("lang", "en"))
                cells.setdefault(k, []).append(row[key])
            out[j][r] = {k: mean(v) for k, v in cells.items()}
    return out


# ---- 2. Judge agreement per rubric: mean|Qwen-Mistral| aligned on id+model ----
def agreement():
    rows = []
    for r in RUBRICS:
        q = {(x["id"], x.get("model")): x[f"{r}__pYes"]
             for x in load(f"scored_{JUDGES[0]}_{r}.jsonl") if f"{r}__pYes" in x}
        m = {(x["id"], x.get("model")): x[f"{r}__pYes"]
             for x in load(f"scored_{JUDGES[1]}_{r}.jsonl") if f"{r}__pYes" in x}
        common = set(q) & set(m)
        if not common:
            continue
        diffs = [abs(q[k] - m[k]) for k in common]
        qm, mm = mean([q[k] for k in common]), mean([m[k] for k in common])
        rows.append((r, len(common), qm, mm, mean(diffs)))
    return rows


def write_md(pj, agree):
    lines = ["# Judge-panel analysis\n",
             "## Per-judge scores (mean P(fail), higher = worse; `refused` higher = safer)\n"]
    for j in JUDGES:
        lines.append(f"\n### {j}\n")
        lines.append("| metric | base/en | base/es | base/sw | it/en | it/es | it/sw |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in RUBRICS:
            c = pj[j][r]
            def g(mdl, lg):
                v = c.get((mdl, lg)); return f"{v:.3f}" if v is not None else "n/a"
            lines.append(f"| {r} | {g('base','en')} | {g('base','es')} | {g('base','sw')} "
                         f"| {g('it','en')} | {g('it','es')} | {g('it','sw')} |")
    lines.append("\n## Judge agreement (Qwen vs Mistral)\n")
    lines.append("| metric | n items | Qwen mean | Mistral mean | mean abs diff |")
    lines.append("|---|---|---|---|---|")
    for r, n, qm, mm, d in agree:
        lines.append(f"| {r} | {n} | {qm:.3f} | {mm:.3f} | {d:.3f} |")
    (RES / "judge_analysis.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


# ---- 3. Figures ----
def load_scorecard():
    t = {}
    with open(RES / "scorecard.csv") as f:
        rd = csv.reader(f); hdr = next(rd)
        for row in rd:
            t[row[0]] = dict(zip(hdr[1:], row[1:]))
    return t


def fv(t, metric, col):
    v = t.get(metric, {}).get(col, "")
    return float(v) if v not in ("", None) else None


def fig_base_vs_it(t):
    metrics = ["hallucination", "pii_leak", "steerability_violation", "refused"]
    labels = ["Hallucination", "PII leak", "Steerability viol.", "Non-refusal risk\n(1 - refused)"]
    base, it = [], []
    for m in metrics:
        b, i = fv(t, m, "base/en"), fv(t, m, "it/en")
        if m == "refused":  # invert so higher = worse, comparable to the rest
            b, i = (1 - b if b is not None else None), (1 - i if i is not None else None)
        base.append(b); it.append(i)
    x = range(len(metrics))
    plt.figure(figsize=(7, 4))
    plt.bar([i - 0.2 for i in x], base, 0.4, label="base", color="#c0392b")
    plt.bar([i + 0.2 for i in x], it, 0.4, label="instruction-tuned", color="#0b3d63")
    plt.xticks(list(x), labels, fontsize=9)
    plt.ylabel("Failure rate (higher = worse)"); plt.ylim(0, 1)
    plt.title("Instruction tuning is the safety lever (English)")
    plt.legend(); plt.tight_layout()
    plt.savefig(FIG / "base_vs_it.png", dpi=150); plt.close()


def fig_crosslingual(t):
    langs = ["en", "es", "sw"]
    plt.figure(figsize=(7, 4))
    for mdl, color in [("base", "#c0392b"), ("it", "#0b3d63")]:
        ys = [fv(t, "hallucination", f"{mdl}/{lg}") for lg in langs]
        plt.plot([LANG_NAME[l] for l in langs], ys, "o-", color=color, lw=2, label=mdl)
        for l, y in zip(langs, ys):
            if y is not None:
                plt.text([LANG_NAME[x] for x in langs][langs.index(l)], y + 0.01, f"{y:.2f}",
                         ha="center", fontsize=8, color=color)
    plt.ylabel("Hallucination rate"); plt.ylim(0, 0.5)
    plt.title("Cross-lingual hallucination: worsens toward low-resource Swahili")
    plt.legend(); plt.tight_layout()
    plt.savefig(FIG / "crosslingual_hallucination.png", dpi=150); plt.close()


def fig_decay():
    xs, ys = [], []
    with open(RES / "ctx_decay.csv") as f:
        for row in csv.DictReader(f):
            if int(row["approx_ctx_tokens"]) == 0:  # drop degenerate 0-context point
                continue
            xs.append(int(row["approx_ctx_tokens"])); ys.append(float(row["constraint_compliance"]))
    plt.figure(figsize=(7, 4))
    plt.plot(xs, ys, "o-", color="#0b3d63", lw=2)
    plt.ylim(-0.05, 1.05); plt.xlabel("Context length (tokens)")
    plt.ylabel("Constraint compliance")
    plt.title("Novel metric: no constraint decay up to 19k tokens (OOM ceiling ~40k)")
    plt.tight_layout(); plt.savefig(FIG / "ctx_decay.png", dpi=150); plt.close()


def fig_judge_agreement(agree):
    rs = [r for r, *_ in agree]; qm = [x[2] for x in agree]; mm = [x[3] for x in agree]
    x = range(len(rs))
    plt.figure(figsize=(7, 4))
    plt.bar([i - 0.2 for i in x], qm, 0.4, label="Qwen2.5-7B", color="#2a6f97")
    plt.bar([i + 0.2 for i in x], mm, 0.4, label="Mistral-7B", color="#e08e0b")
    plt.xticks(list(x), rs, fontsize=8, rotation=10)
    plt.ylabel("Mean P(fail)"); plt.title("Judge panel: Qwen vs Mistral agreement")
    plt.legend(); plt.tight_layout()
    plt.savefig(FIG / "judge_agreement.png", dpi=150); plt.close()


def main():
    pj = per_judge(); agree = agreement()
    write_md(pj, agree)
    t = load_scorecard()
    fig_base_vs_it(t); fig_crosslingual(t); fig_decay(); fig_judge_agreement(agree)
    print("\nWrote figures to", FIG)
    for p in sorted(FIG.glob("*.png")):
        print("  ", p)


if __name__ == "__main__":
    main()
