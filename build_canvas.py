#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scene-flow 画布构建脚本
用法: python3 build_canvas.py [剧本.json] [-o 输出.html]
职责: 读剧本 → 校验(连线端点/泳道重叠/场景覆盖) → 注入模板 → 输出自包含 HTML
改剧本只改 剧本.json，重跑本命令即出新画布，不改任何代码。
"""
import json, re, sys, os
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "剧本.json")
TEMPLATE = os.path.join(HERE, "画布模板.html")
DEFAULT_OUT = os.path.join(HERE, "场景串联画布-v0.1.html")

def load_args():
    script, out = SCRIPT, DEFAULT_OUT
    args = sys.argv[1:]
    if args and args[0].endswith(".json"):
        script = args[0]; args = args[1:]
    if "-o" in args:
        i = args.index("-o"); out = args[i+1]
    return script, out

def validate(d):
    warn, err = [], []

    # 1) 连线端点存在
    ids = {n["id"] for n in d["nodes"]} | {f"pool:{p['id']}" for p in d["pools"]}
    for l in d.get("links", []):
        for k in ("from", "to"):
            if l[k] not in ids:
                err.append(f"连线端点不存在: {l[k]} (label: {l.get('label','?')})")

    # 2) 同格冲突：同一 链序×泳道 只能有一个节点
    cell = {}
    for n in d["nodes"]:
        key = (n["seq"], n["lane"])
        if key in cell:
            err.append(f"链序[{n['seq']}] 泳道[{n['lane']}] 已有节点 {cell[key]}，又放入 {n['id']}")
        else:
            cell[key] = n["id"]

    # 3) 场景覆盖核对
    covered = OrderedDict()
    for group in ("nodes", "events", "cycles"):
        for item in d.get(group, []):
            for s in item.get("scenes", []):
                covered.setdefault(s, []).append(item["title"])
    for step in ([d.get("skillLoop", {}).get("left", {}), d.get("skillLoop", {}).get("right", {})]):
        for s in step.get("scenes", []):
            covered.setdefault(s, []).append(step["title"])
    exec_g = {s: v for s, v in covered.items() if s.startswith("高管")}
    gen_g  = {s: v for s, v in covered.items() if s.startswith("通用")}
    expected = d["meta"].get("expectedScenes", 0)
    total = len(covered)
    print("── 场景覆盖核对 ──")
    print(f"高管: {len(exec_g)}/13  通用: {len(gen_g)}/8  合计 {total} (剧本声明 expectedScenes={expected})")
    for s, v in covered.items():
        print(f"  ✓ {s}  ← {('、'.join(v))[:40]}")
    if expected and total != expected:
        err.append(f"场景覆盖数 {total} ≠ expectedScenes {expected}")
    # 缺口提示
    miss_exec = [f"高管{i:02d}" for i in range(1,14) if f"高管{i:02d}" not in covered]
    miss_gen  = [f"通用{i:02d}" for i in range(1,9) if f"通用{i:02d}" not in covered]
    if miss_exec: warn.append("高管未覆盖: " + "、".join(miss_exec))
    if miss_gen:  warn.append("通用未覆盖: " + "、".join(miss_gen))

    return warn, err

def main():
    script, out = load_args()
    with open(script, encoding="utf-8") as f:
        d = json.load(f)
    with open(TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()

    warn, err = validate(d)
    for w in warn: print("⚠ ", w)
    if err:
        for e in err: print("✗ ", e)
        sys.exit(1)

    m = d["meta"]
    loop = d.get("skillLoop", {})
    html = (tpl
        .replace("__PAGE_TITLE__", m["title"].replace("<em>", "").replace("</em>", ""))
        .replace("__PAGE_TITLE_HTML__", m["title"])
        .replace("__PAGE_KICKER__", m["kicker"])
        .replace("__PAGE_SUBTITLE__", m["subtitle"])
        .replace("__LOOP_TITLE__", loop.get("title", ""))
        .replace("__LOOP_SUB__", loop.get("sub", ""))
        .replace("__LOOP_NOTE__", loop.get("loopNote", ""))
        .replace("__SCENE_DATA__", json.dumps(d, ensure_ascii=False, separators=(",", ":")))
    )
    leftover = re.findall(r"__[A-Z_]+__", html)
    if leftover:
        print("✗ 模板存在未替换占位符:", set(leftover)); sys.exit(1)

    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("── 构建完成 ──")
    print(f"✓ {out}  ({os.path.getsize(out)//1024} KB)")
    print(f"  节点 {len(d['nodes'])} · 连线 {len(d['links'])} · 随时事件 {len(d['events'])} · 周期事件 {len(d['cycles'])} · 地基池 {len(d['pools'])}")

if __name__ == "__main__":
    main()
