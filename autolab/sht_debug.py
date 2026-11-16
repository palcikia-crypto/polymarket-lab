"""Дебаг sht_scan: повторяет фильтры воркера и показывает, где пропадают окна. Пишет results/sht_debug.json."""
import json, os, re, time, urllib.request

GAMMA = "https://gamma-api.polymarket.com"
BIN = "https://data-api.binance.vision/api/v3/klines"
UA = {"User-Agent": "pm-lab-debug/1.0"}

def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

def plist(s):
    try: return json.loads(s)
    except Exception: return []

def fnum(x):
    try: return float(x or 0)
    except Exception: return 0.0

SERIES = [
    ("btc-up-or-down-5m", "BTCUSDT", 300, "sht5"),
    ("btc-up-or-down-15m", "BTCUSDT", 900, "sht15"),
    ("btc-up-or-down-1h", "BTCUSDT", 3600, "sht1h"),
    ("eth-up-or-down-5m", "ETHUSDT", 300, "sht5"),
    ("eth-up-or-down-15m", "ETHUSDT", 900, "sht15"),
    ("sol-up-or-down-5m", "SOLUSDT", 300, "sht5"),
]

def main():
    t_now = time.time()
    rep = {"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "now_ts": int(t_now), "series": {}}
    for series_slug, sym, win_s, tag in SERIES:
        d = {"evs": 0, "kept": 0, "reject": {}}
        try:
            evs = fetch(GAMMA + "/events?series_slug=" + series_slug + "&closed=false&limit=60&order=endDate&ascending=false", 12)
            d["evs"] = len(evs) if isinstance(evs, list) else -1
            for ev in (evs or []):
                slug = ev.get("slug", "")
                mm = re.search(r"(\d{9,})$", slug)
                if not mm:
                    d["reject"]["no_ts"] = d["reject"].get("no_ts", 0) + 1; continue
                start = int(mm.group(1)); end = start + win_s
                if end < t_now:
                    d["reject"]["end_past"] = d["reject"].get("end_past", 0) + 1; continue
                mkt = ev if ev.get("outcomePrices") else (ev.get("markets") or [{}])[0]
                pr = [fnum(x) for x in plist(mkt.get("outcomePrices", "[]"))]
                if len(pr) != 2 or pr[0] <= 0:
                    d["reject"]["no_prices"] = d["reject"].get("no_prices", 0) + 1; continue
                d["kept"] += 1
                if d["kept"] <= 2:
                    d.setdefault("sample", []).append({"slug": slug, "start": start, "end": end, "pr": pr})
        except Exception as e:
            d["error"] = "%s: %s" % (type(e).__name__, e)
        rep["series"][series_slug] = d
    os.makedirs("results", exist_ok=True)
    with open("results/sht_debug.json", "w") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print("sht_debug done")

if __name__ == "__main__":
    main()
