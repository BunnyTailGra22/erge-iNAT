#!/usr/bin/env python3
"""AI flower-suggestion layer (vision model). For each historical observation,
aggregate ALL its photos and ask a vision model whether the plant is FLOWERING
(open flowers; tight buds do NOT count), with a confidence score. Writes an
independent suggestion layer — NOT merged into iNaturalist annotations.

Output: data/phenophase/ai_flower.json  { obs_id: {flower, confidence, n_photos, model, at} }

Needs ANTHROPIC_API_KEY. The current data/phenophase/ai_flower.json was seeded by a
manual Claude-vision demo batch (ERG-052); run this to scale to all records.

Usage:
  python3 ai_flower.py --unit ERG-052          # one unit
  python3 ai_flower.py --all --skip-annotated  # everything iNat hasn't already flagged as flower
  python3 ai_flower.py --all --limit 50        # cap (cost control)
"""
import argparse, json, os, datetime, urllib.request, urllib.parse, time, base64

HERE = os.path.dirname(os.path.abspath(__file__))
RECS = os.path.join(HERE, "data", "history", "records.json")
OUT = os.path.join(HERE, "data", "phenophase", "ai_flower.json")
UNITS = os.path.join(HERE, "data", "registry", "units.json")
MODEL = os.environ.get("VISION_MODEL", "claude-sonnet-4-6")
MAX_PHOTOS = 6   # per observation, to cap tokens/cost

PROMPT = (
    "You are scoring plant phenology from iNaturalist photos. These photos are ALL from "
    "ONE observation of {sci} ({common}). Looking across all of them, is the plant "
    "FLOWERING — i.e. at least one OPEN flower is visible? Tight unopened flower buds, "
    "fruit, or leaves-only do NOT count as flowering. "
    "Reply with ONLY compact JSON: {{\"flower\": true|false, \"confidence\": 0.0-1.0}}."
)


def obs_photos(obs_id):
    """Fetch all photo URLs (medium) for one observation."""
    url = f"https://api.inaturalist.org/v1/observations/{obs_id}"
    d = json.load(urllib.request.urlopen(url))
    r = (d.get("results") or [{}])[0]
    return [(p.get("photo") or p).get("url", "").replace("square", "medium")
            for p in (r.get("photos") or [])]


def classify(sci, common, photo_urls):
    """Call the Anthropic vision API; return (flower, confidence)."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("set ANTHROPIC_API_KEY to run the vision model "
                         "(the committed ai_flower.json is a manual demo batch).")
    content = [{"type": "image", "source": {"type": "url", "url": u}}
               for u in photo_urls[:MAX_PHOTOS]]
    content.append({"type": "text", "text": PROMPT.format(sci=sci, common=common or "")})
    body = json.dumps({"model": MODEL, "max_tokens": 100,
                       "messages": [{"role": "user", "content": content}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    d = json.load(urllib.request.urlopen(req))
    txt = "".join(b.get("text", "") for b in d.get("content", []))
    j = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
    return bool(j.get("flower")), float(j.get("confidence", 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit"); ap.add_argument("--all", action="store_true")
    ap.add_argument("--skip-annotated", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    recs = json.load(open(RECS))
    cache = json.load(open(OUT)) if os.path.exists(OUT) else {}
    units = {u["unit_id"]: u for u in json.load(open(UNITS))}

    todo = recs
    if a.unit:
        todo = [r for r in recs if r["unit_id"] == a.unit]
    if a.skip_annotated:
        todo = [r for r in todo if "flower" not in (r["phenophase"] or "")]
    todo = [r for r in todo if str(r["obs_id"]) not in cache]
    if a.limit:
        todo = todo[:a.limit]

    print(f"classifying {len(todo)} observations with {MODEL} …")
    for i, r in enumerate(todo, 1):
        u = units.get(r["unit_id"], {})
        try:
            photos = obs_photos(r["obs_id"])
            if not photos:
                continue
            fl, conf = classify(u.get("scientific"), u.get("common"), photos)
            cache[str(r["obs_id"])] = {"flower": fl, "confidence": round(conf, 2),
                                       "n_photos": len(photos), "model": MODEL,
                                       "at": datetime.date.today().isoformat()}
            print(f"  [{i}/{len(todo)}] {r['obs_id']} {u.get('common','')}: "
                  f"flower={fl} conf={conf:.2f} ({len(photos)} photos)")
        except Exception as e:
            print(f"  [{i}] {r['obs_id']} error: {e}")
        time.sleep(0.5)
        if i % 20 == 0:
            json.dump(cache, open(OUT, "w"), ensure_ascii=False, indent=2)
    json.dump(cache, open(OUT, "w"), ensure_ascii=False, indent=2)
    print(f"wrote {OUT} ({len(cache)} obs)")


if __name__ == "__main__":
    main()
