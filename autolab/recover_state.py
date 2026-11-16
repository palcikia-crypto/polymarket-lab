"""Одноразовое восстановление state.json из git-истории (файл побился при миграции 10.11,
затем 16.11 перезаписан дефолтом). Парсит старый файл толерантно к мусору в хвосте."""
import json, os

OLD = "results/old_state.json"
CUR = "results/state.json"

def raw_json(text):
    try:
        obj, _ = json.JSONDecoder().raw_decode(text.lstrip())
        return obj
    except Exception:
        return None

def main():
    if not os.path.exists(OLD):
        print("recover: old file отсутствует - пропуск")
        return
    with open(OLD, encoding="utf-8", errors="replace") as f:
        txt = f.read()
    old = raw_json(txt)
    if old is None:
        i = txt.rfind("}")
        if i > 0:
            old = raw_json(txt[:i + 1])
    if not isinstance(old, dict) or not isinstance(old.get("cash"), (int, float)) or not isinstance(old.get("positions"), dict):
        print("recover: старый state не распознан - пропуск")
        return
    cur = {}
    if os.path.exists(CUR):
        try:
            with open(CUR) as f: cur = json.load(f)
        except Exception:
            cur = {}
    merged = dict(old)
    merged["runs"] = int(old.get("runs", 0)) + int(cur.get("runs", 0))
    oc = old.get("curve") or []
    curve = list(oc) + [x for x in (cur.get("curve") or []) if x not in oc]
    merged["curve"] = curve[-1500:]
    with open(CUR, "w") as f:
        json.dump(merged, f, ensure_ascii=False, indent=1)
    os.remove(OLD)
    print("recover: восстановлено cash=%.2f, позиций=%d, закрытых=%d" % (
        merged["cash"], len(merged["positions"]), len(merged.get("closed") or [])))

if __name__ == "__main__":
    main()
