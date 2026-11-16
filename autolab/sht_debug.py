"""Дебаг sht_scan v2: матрица вариантов запроса событий (UA x параметры), ищем какой проходит."""
import json, os, re, time, urllib.request, urllib.error

GAMMA = "https://gamma-api.polymarket.com"

UAS = ["pm-lab/2.0", "pm-lab-debug/1.0", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"]

def fetch(url, ua, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

def main():
    rep = {"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "variants": []}
    base = GAMMA + "/events?series_slug=btc-up-or-down-5m&closed=false&limit=5&order=endDate"
    variants = [
        base + "&ascending=false",
        base + "&ascending=true",
        GAMMA + "/events?series_slug=btc-up-or-down-5m&closed=false&limit=5",
        GAMMA + "/events?slug=btc-updown-5m-1794882000",
    ]
    for ua in UAS:
        for v in variants:
            entry = {"ua": ua, "url_tail": v.replace(GAMMA, ""), "ok": None}
            try:
                d = fetch(v, ua)
                entry["ok"] = True
                entry["n"] = len(d) if isinstance(d, list) else "dict"
                if isinstance(d, list) and d:
                    e0 = d[0]
                    entry["first_slug"] = e0.get("slug")
                    src = e0 if e0.get("outcomePrices") else (e0.get("markets") or [{}])[0]
                    entry["first_prices"] = src.get("outcomePrices")
            except urllib.error.HTTPError as e:
                entry["ok"] = False
                entry["err"] = "HTTP %d" % e.code
            except Exception as e:
                entry["ok"] = False
                entry["err"] = "%s: %s" % (type(e).__name__, str(e)[:80])
            rep["variants"].append(entry)
            time.sleep(0.4)
    os.makedirs("results", exist_ok=True)
    with open("results/sht_debug.json", "w") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print("sht_debug v2 done")

if __name__ == "__main__":
    main()
