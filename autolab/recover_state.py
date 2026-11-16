"""Восстановление state.json: v3.1. Достаёт cash + открытые позиции даже из
обрезанного файла (баланс скобок). История закрытых сделок, увы, не восстановится."""
import json, os, re, subprocess, time, traceback

CUR = "results/state.json"
LOG = "results/recover_log.txt"
PATH = "results/state.json"

def raw_json(text):
    try:
        obj, _ = json.JSONDecoder().raw_decode(text.lstrip())
        return obj
    except Exception:
        return None

def balanced_fragment(txt, start):
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(txt)):
        ch = txt[i]
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': in_str = False
            continue
        if ch == '"': in_str = True
        elif ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return txt[start:i + 1]
    return None

def salvage(txt):
    st = {}
    m = re.search(r'"cash"\s*:\s*([0-9.]+)', txt)
    if m: st["cash"] = float(m.group(1))
    i = txt.find('"positions"')
    if i >= 0:
        j = txt.find('{', i)
        frag = balanced_fragment(txt, j) if j >= 0 else None
        if frag:
            try:
                pos = json.loads(frag)
                if isinstance(pos, dict):
                    st["positions"] = pos
            except Exception:
                pass
    return st if ("cash" in st or "positions" in st) else None

def score(st):
    if not isinstance(st, dict): return -1
    if not isinstance(st.get("cash"), (int, float)) or not isinstance(st.get("positions"), dict): return -1
    return len(st.get("closed") or []) * 10 + len(st.get("positions") or {}) + min(len(st.get("curve") or []), 100) / 100.0

def main():
    lines = []
    try:
        shas = subprocess.run(["git", "log", "--format=%H", "--", PATH],
                              capture_output=True, text=True, timeout=60).stdout.split()
        lines.append("commits: %d" % len(shas))
        best, best_sc, best_src = None, -1, None
        for sha in shas:
            try:
                r = subprocess.run(["git", "show", "%s:%s" % (sha, PATH)],
                                   capture_output=True, text=True, timeout=30)
                if r.returncode != 0: continue
                txt = r.stdout
                st = raw_json(txt)
                src = "full"
                if st is None:
                    st = salvage(txt)
                    src = "salvage"
                sc = score(st)
                lines.append("%s len=%d src=%s score=%s" % (sha[:8], len(txt), src, sc))
                if sc > best_sc:
                    best, best_sc, best_src = st, sc, (sha[:8], src)
            except Exception as e:
                lines.append("%s error %s" % (sha[:8], e))
        cur, cur_sc = None, -1
        if os.path.exists(CUR):
            try:
                with open(CUR) as f: cur = json.load(f)
                cur_sc = score(cur)
            except Exception: pass
        lines.append("best=%s cur=%s" % (best_sc, cur_sc))
        if best is not None and best_sc > cur_sc:
            merged = dict(best)
            merged.setdefault("closed", [])
            merged.setdefault("curve", [[time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), round(merged.get("cash", 1000.0), 2)]])
            merged.setdefault("done_keys", {})
            merged.setdefault("cal", [])
            if cur is not None and cur_sc >= 0:
                merged["runs"] = int(best.get("runs", 0)) + int(cur.get("runs", 0))
            with open(CUR, "w") as f:
                json.dump(merged, f, ensure_ascii=False, indent=1)
            lines.append("RESTORED from %s cash=%.2f positions=%d" % (
                best_src, merged.get("cash", 0), len(merged.get("positions") or {})))
        else:
            lines.append("текущий не хуже - не трогаю")
    except Exception:
        lines.append(traceback.format_exc())
    finally:
        with open(LOG, "w") as f:
            f.write("\n".join(lines) + "\n")

if __name__ == "__main__":
    main()
