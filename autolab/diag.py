"""Диагностика API для pm-lab: что именно отвечает Polymarket/Binance из GitHub Actions.
Пишет results/diag.json. Не торгует, только проверяет.
"""
import json, os, time, urllib.request, urllib.error

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
BIN = "https://data-api.binance.vision/api/v3/klines"
OUT = "results/diag.json"
UA = {"User-Agent": "pm-lab-diag/1.0"}

def probe(url, timeout=10):
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
        head = body[:300].replace("\n", " ")
        try:
            j = json.loads(body)
            shape = ("list[%d]" % len(j)) if isinstance(j, list) else ("dict keys: " + ",".join(list(j.keys())[:8]))
        except Exception:
            shape = "not-json"
        return {"url": url, "ok": True, "ms": int((time.time() - t0) * 1000), "shape": shape, "head": head, "_body": body}
    except urllib.error.HTTPError as e:
        try: head = e.read()[:200].decode("utf-8", "replace").replace("\n", " ")
        except Exception: head = ""
        return {"url": url, "ok": False, "ms": int((time.time() - t0) * 1000), "error": "HTTP %d" % e.code, "head": head}
    except Exception as e:
        return {"url": url, "ok": False, "ms": int((time.time() - t0) * 1000), "error": "%s: %s" % (type(e).__name__, e)}

def getjson(url, timeout=10):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

def main():
    res = {"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "probes": []}
    p = res["probes"]

    url1 = GAMMA + "/markets?tag_id=21&closed=false&active=true&limit=3&order=volume24hr&ascending=false"
    r1 = probe(url1)
    mid, tokens = None, None
    if r1.get("ok"):
        try:
            ms = json.loads(r1["_body"])
            if isinstance(ms, list) and ms:
                m0 = ms[0]
                mid = m0.get("id")
                res["sample_market"] = {"id": mid, "slug": m0.get("slug"), "outcomePrices": m0.get("outcomePrices"),
                                        "clobTokenIds": (m0.get("clobTokenIds") or "")[:200],
                                        "acceptingOrders": m0.get("acceptingOrders")}
                try: tokens = json.loads(m0.get("clobTokenIds", "[]"))
                except Exception: tokens = None
        except Exception as e:
            res["sample_market_error"] = str(e)
    r1.pop("_body", None)
    p.append(r1)

    if mid:
        rh = probe(GAMMA + "/markets/%s/prices-history?interval=1w&fidelity=60" % mid)
        rh.pop("_body", None)
        p.append(rh)

    r4 = probe(BIN + "?symbol=BTCUSDT&interval=1m&limit=5")
    r4.pop("_body", None)
    p.append(r4)

    # серия Up or Down: свежие первыми, смотрим что реально возвращается
    r6 = probe(GAMMA + "/events?series_slug=btc-up-or-down-5m&closed=false&limit=5&order=endDate&ascending=false")
    if r6.get("ok"):
        try:
            evs = json.loads(r6["_body"])
            res["sht_newest"] = []
            for e in (evs or [])[:5]:
                src = e if e.get("outcomePrices") else (e.get("markets") or [{}])[0]
                res["sht_newest"].append({"slug": e.get("slug"), "endDate": e.get("endDate"),
                                          "closed": e.get("closed"), "active": e.get("active"),
                                          "outcomePrices": src.get("outcomePrices")})
        except Exception as e:
            res["sht_newest_error"] = str(e)
    r6.pop("_body", None)
    p.append(r6)

    r7 = probe(GAMMA + "/public-search?q=Bitcoin%20Up%20or%20Down&limit_per_type=5")
    if r7.get("ok"):
        try:
            ps = json.loads(r7["_body"])
            evs = (ps.get("events") or [])[:5]
            res["search_events"] = [{"slug": e.get("slug"), "endDate": e.get("endDate"), "closed": e.get("closed")} for e in evs]
        except Exception as e:
            res["search_error"] = str(e)
    r7.pop("_body", None)
    p.append(r7)

    if tokens and isinstance(tokens, list) and tokens:
        rb = probe(CLOB + "/book?token_id=" + str(tokens[0]))
        rb.pop("_body", None)
        p.append(rb)
        if rb.get("ok"):
            try:
                book = getjson(CLOB + "/book?token_id=" + str(tokens[0]))
                bids = book.get("bids") or []
                asks = book.get("asks") or []
                best_bid = float(bids[-1]["price"]) if bids else None
                best_ask = float(asks[-1]["price"]) if asks else None
                gamma_price = None
                try:
                    gamma_price = json.loads(getjson(url1)[0].get("outcomePrices", "[]"))[0]
                except Exception:
                    pass
                res["book_vs_gamma"] = {"best_bid": best_bid, "best_ask": best_ask,
                                        "spread": round(best_ask - best_bid, 4) if best_bid and best_ask else None,
                                        "gamma_price": gamma_price,
                                        "delta_ask_minus_gamma": round(best_ask - float(gamma_price), 4) if best_ask and gamma_price else None,
                                        "bid_levels": len(bids), "ask_levels": len(asks)}
            except Exception as e:
                res["book_error"] = str(e)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("diag done: %d probes, ok=%d" % (len(p), sum(1 for x in p if x.get("ok"))))

if __name__ == "__main__":
    main()
