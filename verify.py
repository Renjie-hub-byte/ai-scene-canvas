#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""程序化几何验证：连线锚点 / 文字溢出 / 标签压卡 / 池卡溢出"""
import asyncio, pathlib
from playwright.async_api import async_playwright

HTML = pathlib.Path(__file__).parent / "场景串联画布-v0.1.html"

JS = """
() => {
  const problems = [];
  const $ = s => document.querySelector(s);

  /* 1) 节点卡：除有省略号设计的 .pr/.ds 外，任何子元素不得溢出 */
  document.querySelectorAll('.node, .pool').forEach(card=>{
    const name = card.classList.contains('pool') ? card.querySelector('.pn').textContent : card.querySelector('.tt').textContent;
    card.querySelectorAll('.tt, .ds, .pn, .pd, .pf, .row1, .foot .bd').forEach(sub=>{
      if (sub.scrollHeight > sub.clientHeight + 2)
        problems.push(`[垂直溢出] ${name} · ${sub.className}: ${sub.scrollHeight}>${sub.clientHeight}`);
      if (sub.scrollWidth > sub.clientWidth + 2 && !sub.classList.contains('pr') && !sub.classList.contains('pd'))
        problems.push(`[横向溢出] ${name} · ${sub.className}: ${sub.scrollWidth}>${sub.clientWidth}`);
    });
  });

  /* 2) 连线终点必须贴住目标元素边缘（误差<=3px） */
  const box = el => { const r = el.getBoundingClientRect();
    const c = document.getElementById('canvas').getBoundingClientRect();
    return {l:r.left-c.left, t:r.top-c.top, r:r.right-c.left, b:r.bottom-c.top, cx:(r.left+r.right)/2-c.left, cy:(r.top+r.bottom)/2-c.top}; };
  const nodeEls = {}; document.querySelectorAll('.node').forEach(n=>nodeEls[n.dataset.id]=n);
  const poolEls = {}; document.querySelectorAll('.pool').forEach(p=>poolEls['pool:'+p.dataset.id.replace('pool:','')]=p);
  DATA.links.forEach((l,i)=>{
    const path = l._el; if(!path) { problems.push(`[缺线] #${i}`); return; }
    const d = path.getAttribute('d');
    const nums = d.match(/-?\\d+(\\.\\d+)?/g).map(Number);
    const ex = nums[nums.length-2], ey = nums[nums.length-1];
    const tgt = l.to.startsWith('pool:') ? poolEls[l.to] : nodeEls[l.to];
    const src = l.from.startsWith('pool:') ? poolEls[l.from] : nodeEls[l.from];
    if (!tgt || !src) { problems.push(`[缺元素] #${i} ${l.from}->${l.to}`); return; }
    const tb = box(tgt), sb = box(src);
    const onEdge = (p, b) => Math.min(Math.abs(p.x-b.l),Math.abs(p.x-b.r)) < 3.5 || Math.min(Math.abs(p.y-b.t),Math.abs(p.y-b.b)) < 3.5;
    const inRect = (p,b,m=2) => p.x>=b.l-m && p.x<=b.r+m && p.y>=b.t-m && p.y<=b.b+m;
    if (!inRect({x:ex,y:ey}, tb, 3.5)) problems.push(`[终点悬空] #${i} ${l.label}: 终点(${ex.toFixed(0)},${ey.toFixed(0)}) 不在目标边缘`);
    const sx = nums[0], sy = nums[1];
    if (!inRect({x:sx,y:sy}, sb, 3.5)) problems.push(`[起点悬空] #${i} ${l.label}: 起点(${sx.toFixed(0)},${sy.toFixed(0)}) 不在源边缘`);
  });

  /* 3) 连线 label 不得压住任何节点卡 */
  document.querySelectorAll('svg.wires text').forEach(t=>{
    const tr = t.getBoundingClientRect();
    const c = document.getElementById('canvas').getBoundingClientRect();
    const tb = {l:tr.left-c.left, t:tr.top-c.top, r:tr.right-c.left, b:tr.bottom-c.top};
    document.querySelectorAll('.node').forEach(n=>{
      const nb = box(n);
      const overlap = !(tb.r<nb.l-2 || tb.l>nb.r+2 || tb.b<nb.t-2 || tb.t>nb.b+2);
      if (overlap) problems.push(`[标签压卡] "${t.textContent}" 压到节点 "${n.querySelector('.tt').textContent}"`);
    });
  });

  /* 4) 抽屉气泡不溢出 */
  return problems.length ? problems : ['ALL-CLEAN'];
}
"""

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page(viewport={"width":1440,"height":980})
        await pg.goto(HTML.as_uri())
        await pg.wait_for_timeout(500)
        res = await pg.evaluate(JS)
        print("\n".join(res) if isinstance(res, list) else res)

        # 抽屉内气泡溢出抽查：把每个节点/事件/周期都开一遍，检查 .bub 是否横向溢出
        bub_problems = []
        n_items = await pg.evaluate("DATA.nodes.length + DATA.events.length + DATA.cycles.length")
        for i in range(await pg.evaluate("DATA.nodes.length")):
            await pg.evaluate(f"openNode(DATA.nodes[{i}].id)")
            await pg.wait_for_timeout(60)
            bad = await pg.evaluate("""[...document.querySelectorAll('.bub')].filter(b=>b.scrollWidth>b.clientWidth+2).map(b=>b.textContent.slice(0,20))""")
            if bad: bub_problems.append((f"node:{await pg.evaluate(f'DATA.nodes[{i}].id')}", bad))
        for i in range(await pg.evaluate("DATA.events.length")):
            await pg.evaluate(f"openEvent({i})")
            await pg.wait_for_timeout(60)
            bad = await pg.evaluate("""[...document.querySelectorAll('.bub')].filter(b=>b.scrollWidth>b.clientWidth+2).map(b=>b.textContent.slice(0,20))""")
            if bad: bub_problems.append((f"event:{i}", bad))
        for i in range(await pg.evaluate("DATA.cycles.length")):
            await pg.evaluate(f"openCycle({i})")
            await pg.wait_for_timeout(60)
            bad = await pg.evaluate("""[...document.querySelectorAll('.bub')].filter(b=>b.scrollWidth>b.clientWidth+2).map(b=>b.textContent.slice(0,20))""")
            if bad: bub_problems.append((f"cycle:{i}", bad))
        await pg.evaluate("closeSheet()")
        print("── 抽屉气泡检查 ──")
        print("\n".join(f"{k}: {v}" for k,v in bub_problems) if bub_problems else "ALL-CLEAN")
        await b.close()

asyncio.run(main())
