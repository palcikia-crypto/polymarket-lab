"""Одноразовое восстановление state.json из git-истории. Пишет лог в results/recover_log.txt."""
import json, os, traceback

OLD = "results/old_state.json"
CUR = "results/state.json"
LOG = "results/recover_log.txt"

def raw_json(text):
    try:
        obj, _ = json.JSONDecoder().raw_decode(text.lstrip())
        return obj
    except Exception:
        return None

def main():
    lines = []
    try:
        if not os.path.exists(OLD):
            lines.append("old file отсутствует - пропуск")
            return
        with open(OLD, encoding="utf-8", errors="replace") as f:
            txt = f.read()
        lines.append("old size=%d head=%r" % (len(txt), txt[:60]))
        old = raw_json(txt)
        if old is None:
            i = txt.rfind("}")
            lines.append("raw_decode failed, retry до позиции %d" % i)
            if i > 0:
                old = raw_json(txt[:i + 1])
        lines.append("parsed=%s" % type(old).__name__)
        ok = isinstance(old, dict) and isinstance(old.get("cash"), (int, float)) and isinstance(old.get("positions"), dict)
        lines.append("valid=%s" % ok)
        if not ok:
            return
        cur = {}
        if os.path.exists(CUR):
            try:
                with open(CUR) as f: cur = json.load(f)
            except Exception as e:
                lines.append("cur unreadable: %s" % e)
        merged = dict(old)
        merged["runs"] = int(old.get("runs", 0)) + int(cur.get("runs", 0))
        oc = old.get("curve") or []
        merged["curve"] = (list(oc) + [x for x in (cur.get("curve") or []) if x not in oc])[-1500:]
        with open(CUR, "w") as f:
            json.dump(merged, f, ensure_ascii=False, indent=1)
        os.remove(OLD)
        lines.append("RESTORED cash=%.2f positions=%d closed=%d" % (merged["cash"], len(merged["positions"]), len(merged.get("closed") or [])))
    except Exception:
        lines.append(traceback.format_exc())
    finally:
        with open(LOG, "w") as f:
            f.write("\n".join(lines) + "\n")

if __name__ == "__main__":
    main()
