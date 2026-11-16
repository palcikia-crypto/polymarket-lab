"""Восстановление state.json из git-истории: перебирает все версии файла,
берёт самую полную валидную. Лог: results/recover_log.txt."""
import json, os, subprocess, traceback

CUR = "results/state.json"
LOG = "results/recover_log.txt"
PATH = "results/state.json"

def raw_json(text):
    try:
        obj, _ = json.JSONDecoder().raw_decode(text.lstrip())
        return obj
    except Exception:
        return None

def score(st):
    if not isinstance(st, dict): return -1
    if not isinstance(st.get("cash"), (int, float)) or not isinstance(st.get("positions"), dict): return -1
    return len(st.get("closed") or []) * 10 + len(st.get("positions") or {}) + min(len(st.get("curve") or []), 100) / 100.0

def main():
    lines = []
    try:
        shas = subprocess.run(["git", "log", "--format=%H", "--", PATH],
                              capture_output=True, text=True, timeout=60).stdout.split()
        lines.append("commits touching %s: %d" % (PATH, len(shas)))
        best, best_sha, best_sc = None, None, -1
        for sha in shas:
            try:
                r = subprocess.run(["git", "show", "%s:%s" % (sha, PATH)],
                                   capture_output=True, text=True, timeout=30)
                if r.returncode != 0: continue
                st = raw_json(r.stdout)
                sc = score(st)
                lines.append("%s len=%d score=%s" % (sha[:8], len(r.stdout), sc))
                if sc > best_sc:
                    best, best_sha, best_sc = st, sha, sc
            except Exception as e:
                lines.append("%s error %s" % (sha[:8], e))
        cur_sc = -1
        cur = None
        if os.path.exists(CUR):
            try:
                with open(CUR) as f: cur = json.load(f)
                cur_sc = score(cur)
            except Exception: pass
        lines.append("best=%s score=%s cur_score=%s" % (best_sha, best_sc, cur_sc))
        if best is not None and best_sc > cur_sc:
            merged = dict(best)
            if cur is not None and cur_sc >= 0:
                merged["runs"] = int(best.get("runs", 0)) + int(cur.get("runs", 0))
                oc = best.get("curve") or []
                merged["curve"] = (list(oc) + [x for x in (cur.get("curve") or []) if x not in oc])[-1500:]
            with open(CUR, "w") as f:
                json.dump(merged, f, ensure_ascii=False, indent=1)
            lines.append("RESTORED from %s cash=%.2f positions=%d closed=%d" % (
                best_sha[:8], merged["cash"], len(merged.get("positions") or {}), len(merged.get("closed") or [])))
        else:
            lines.append("текущий не хуже - не трогаю")
    except Exception:
        lines.append(traceback.format_exc())
    finally:
        with open(LOG, "w") as f:
            f.write("\n".join(lines) + "\n")

if __name__ == "__main__":
    main()
