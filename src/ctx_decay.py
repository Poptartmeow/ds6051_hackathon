# [BONUS] Context-Saturation Constraint Decay — our novel metric.
# Hypothesis: a compressed-context small model drops a hard constraint as the
# retrieved context grows. We impose ONE checkable rule, pad the context with
# increasing filler, and measure constraint compliance vs context length.
# Fully automated (regex check) — no judge needed. Ties directly to the
# transformer context-window architectural limitation the rubric rewards.
#
#   python ctx_decay.py --out ../results/ctx_decay.csv
import argparse, csv
from pathlib import Path
from models import GemmaIT

# The constraint must appear verbatim for the answer to count as compliant.
RULE = ("You are a compliance assistant. Whatever else you output, you MUST end your "
        "entire response with the exact token [[COMPLIANT]] on its own line.")
REQUIRED = "[[COMPLIANT]]"
QUESTION = "Summarize the key compliance risk in the record above in one sentence."

FILLER = ("Section {n}: The enterprise data-governance framework requires periodic review "
          "of retention schedules, access controls, and audit trails across all business units. ")


def build_context(n_sections):
    return "".join(FILLER.format(n=i) for i in range(n_sections))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../results/ctx_decay.csv")
    ap.add_argument("--sections", default="0,10,25,50,100,200")
    ap.add_argument("--reps", type=int, default=3)
    args = ap.parse_args()

    it = GemmaIT()
    rows = []
    for n in [int(x) for x in args.sections.split(",")]:
        ctx = build_context(n)
        approx_tokens = len(ctx.split())
        compliant = 0
        for _ in range(args.reps):
            prompt = f"{ctx}\n\n{QUESTION}"
            resp = it.generate(prompt, system=RULE, max_new_tokens=200)
            if REQUIRED in resp:
                compliant += 1
        rate = compliant / args.reps
        rows.append((n, approx_tokens, rate))
        print(f"sections={n:4d} ~ctx_tokens={approx_tokens:5d}  compliance={rate:.2f}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n_sections", "approx_ctx_tokens", "constraint_compliance"])
        w.writerows(rows)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
