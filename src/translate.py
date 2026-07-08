# Cross-lingual: translate the EN 'refused' probes into Spanish + Swahili (low-resource)
# with NLLB-200, and append the translated rows to prompts.jsonl. Run AFTER build_dataset.
# NLLB is a small seq2seq model (~600M) — fits trivially, run it as its own stage.
#
#   python translate.py --in prompts.jsonl --out prompts.jsonl --langs spa_Latn,swh_Latn
import json, argparse
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

NLLB = "facebook/nllb-200-distilled-600M"
LANG_TAG = {"spa_Latn": "es", "swh_Latn": "sw"}  # swh_Latn = Swahili (low-resource)


def read_jsonl(p):
    with open(p) as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="prompts.jsonl")
    ap.add_argument("--out", default="prompts.jsonl")
    ap.add_argument("--langs", default="spa_Latn,swh_Latn")
    ap.add_argument("--metric", default="refused", help="only translate this metric's EN rows")
    args = ap.parse_args()

    rows = read_jsonl(args.inp)
    src = [r for r in rows if r.get("lang") == "en"
           and r.get("meta", {}).get("metric") == args.metric]
    if not src:
        print("No source rows to translate."); return

    tok = AutoTokenizer.from_pretrained(NLLB)
    model = AutoModelForSeq2SeqLM.from_pretrained(NLLB, torch_dtype=torch.float32).to(
        "cuda" if torch.cuda.is_available() else "cpu")

    new_rows = []
    for tgt in args.langs.split(","):
        tok.src_lang = "eng_Latn"
        bos = tok.convert_tokens_to_ids(tgt)
        for r in src:
            enc = tok(r["prompt"], return_tensors="pt").to(model.device)
            out = model.generate(**enc, forced_bos_token_id=bos, max_new_tokens=256)
            txt = tok.batch_decode(out, skip_special_tokens=True)[0]
            new_rows.append({**r, "id": f'{r["id"]}-{LANG_TAG[tgt]}',
                             "prompt": txt, "lang": LANG_TAG[tgt],
                             "meta": {**r.get("meta", {}), "translated_from": r["id"]}})
        print(f"translated {len(src)} -> {tgt}")

    with open(args.out, "w") as f:
        for r in rows + new_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)+len(new_rows)} rows -> {args.out}")


if __name__ == "__main__":
    main()
