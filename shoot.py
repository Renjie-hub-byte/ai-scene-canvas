#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""画布自检截图：初始态 / 画布右段 / 抽屉详情 / 播放态"""
import asyncio, pathlib
from playwright.async_api import async_playwright

HTML = pathlib.Path(__file__).parent / "场景串联画布-v0.1.html"
OUT = pathlib.Path(__file__).parent / "shots"
OUT.mkdir(exist_ok=True)

async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page(viewport={"width":1440,"height":980})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        await pg.goto(HTML.as_uri())
        await pg.wait_for_timeout(600)

        # 1) 首屏
        await pg.screenshot(path=str(OUT/"01-首屏.png"))

        # 2) 画布滚动到中段（上午）
        await pg.evaluate("document.querySelector('.canvas-scroll').scrollLeft = 700")
        await pg.wait_for_timeout(300)
        cv = await pg.query_selector(".canvas-scroll")
        await cv.screenshot(path=str(OUT/"02-画布中段.png"))

        # 3) 画布右段（下午+skill闭环+地基池）
        await pg.evaluate("document.querySelector('.canvas-scroll').scrollLeft = 9999")
        await pg.wait_for_timeout(300)
        await cv.screenshot(path=str(OUT/"03-画布右段.png"))

        # 4) 点击节点开抽屉
        await pg.evaluate("document.querySelector('.canvas-scroll').scrollLeft = 0")
        await pg.click(".node[data-id='n2']")
        await pg.wait_for_timeout(500)
        await pg.screenshot(path=str(OUT/"04-节点详情抽屉.png"))
        await pg.click("#closeBtn")
        await pg.wait_for_timeout(400)

        # 5) 播放完状态（跳到最后）
        await pg.click("#playBtn")
        await pg.wait_for_timeout(13000)
        await pg.evaluate("document.querySelector('.canvas-scroll').scrollLeft = 9999")
        await pg.wait_for_timeout(300)
        await cv.screenshot(path=str(OUT/"05-播放完成态.png"))

        # 6) 事件带+周期带
        await pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await pg.wait_for_timeout(400)
        await pg.screenshot(path=str(OUT/"06-事件带周期带.png"))

        print("JS错误:", errors if errors else "无")
        await b.close()

asyncio.run(main())
