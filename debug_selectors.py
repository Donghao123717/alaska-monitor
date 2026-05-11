#!/usr/bin/env python3
"""
调试工具 - 截图 + 打印页面结构，帮助找到正确的 CSS 选择器
当网站改版导致脚本失效时，运行这个脚本来重新分析
"""

import yaml
import time
from playwright.sync_api import sync_playwright


def main():
    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)

    route = cfg["routes"][0]
    date = route["dates"][0]
    origin = route["origin"]
    dest = route["destination"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )

        # 登录
        creds = cfg["alaska_account"]
        print("🔐 登录中...")
        page.goto(
            "https://www.alaskaair.com/account/login", wait_until="domcontentloaded"
        )
        time.sleep(4)
        page.wait_for_selector('input[name="username"]', timeout=15_000)
        page.fill('input[name="username"]', creds["username"])
        time.sleep(1)
        page.fill('input[name="password"]', creds["password"])
        time.sleep(1)
        page.evaluate("""
            const buttons = Array.from(document.querySelectorAll('button[type="submit"]'));
            const visible = buttons.find(b => !b.hasAttribute('aria-hidden') && b.offsetParent !== null);
            if (visible) visible.click();
            else buttons[buttons.length - 1].click();
        """)
        print("   等待登录跳转...")
        time.sleep(4)

        # 处理 MFA 弹窗
        try:
            skip_btn = page.locator('button:has-text("Skip for now")')
            if skip_btn.is_visible(timeout=5_000):
                print("   点击 Skip for now...")
                skip_btn.click()
                time.sleep(6)
        except Exception:
            pass
        print(f"   当前URL: {page.url}")

        # 前往搜索页
        url = (
            f"https://www.alaskaair.com/search/calendar"
            f"?O={origin}&D={dest}&OD={date}&A=1&RT=false"
            f"&RequestType=Calendar&ShoppingMethod=onlineaward"
            f"&locale=en-us&FareType=Partner+Business"
        )

        print(f"\n🔍 访问：{url}")
        page.goto(url, wait_until="domcontentloaded")
        time.sleep(8)

        # 截图
        page.screenshot(path="debug_results.png", full_page=True)
        print("📸 截图已保存：debug_results.png")

        # 新增：保存页面纯文本
        text = page.inner_text("body")
        with open("debug_text.txt", "w") as f:
            f.write(text)
        print("📄 页面文本已保存：debug_text.txt")

        # 打印前100行非空内容
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        print(f"\n📋 页面前100行文本：")
        for i, line in enumerate(lines[:100]):
            print(f"  {i:3d}: {line}")

        # 打印页面文本（含 pts 的部分）
        print("\n📋 页面文本前200行：")
        lines = content.split("\n")
        for i, line in enumerate(lines[:200]):
            if line.strip():
                print(f"  {i:3d}: {line.strip()}")

        # 打印所有 class 名（帮助找选择器）
        print("\n📋 页面主要 class 名（含 flight/result/card/row）：")
        classes = page.evaluate("""
            () => {
                const all = document.querySelectorAll('*');
                const names = new Set();
                all.forEach(el => {
                    el.className && el.className.toString().split(' ').forEach(c => {
                        if (c && (c.includes('flight') || c.includes('result') || 
                                  c.includes('card') || c.includes('row') || 
                                  c.includes('fare') || c.includes('price'))) {
                            names.add(c);
                        }
                    });
                });
                return [...names];
            }
        """)
        for c in classes:
            print(f"   .{c}")

        with open("debug_page.html", "w") as f:
            f.write(page.content())
        print("\n📄 完整 HTML 已保存：debug_page.html")

        input("\n按 Enter 关闭...")
        browser.close()


if __name__ == "__main__":
    main()
