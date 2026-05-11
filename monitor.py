#!/usr/bin/env python3
"""
Alaska Airlines Mileage Award Monitor
自动监控里程票商务舱价格，低于阈值时发送邮件提醒
"""

import yaml
import smtplib
import logging
import time
import random
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ── 日志配置 ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("monitor.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ── 配置加载 ──────────────────────────────────────────────
def load_config(path="config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── 邮件发送 ──────────────────────────────────────────────
def send_alert(cfg: dict, results: list[dict]):
    """发送里程票提醒邮件"""
    email_cfg = cfg["email"]
    rows = ""
    for r in results:
        rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #eee">{r['date']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee">{r['origin']} → {r['destination']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee">{r['cabin']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;color:#e63946;font-weight:bold">
            {r['miles']:,} 里程
          </td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee">${r['cash_fee']}</td>
        </tr>"""

    html = f"""
    <html><body style="font-family:sans-serif;color:#222;max-width:680px;margin:0 auto">
      <h2 style="color:#003087">✈️ 阿拉斯加航空里程票提醒</h2>
      <p>以下航班里程低于您设置的阈值，请及时查看：</p>
      <table style="border-collapse:collapse;width:100%;font-size:14px">
        <thead>
          <tr style="background:#003087;color:#fff">
            <th style="padding:10px 12px;text-align:left">日期</th>
            <th style="padding:10px 12px;text-align:left">航线</th>
            <th style="padding:10px 12px;text-align:left">舱位</th>
            <th style="padding:10px 12px;text-align:left">里程</th>
            <th style="padding:10px 12px;text-align:left">税费</th>
            <th style="padding:10px 12px;text-align:left">余座</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="margin-top:20px">
        <a href="https://www.alaskaair.com/shopping/miles/search"
           style="background:#003087;color:#fff;padding:10px 20px;text-decoration:none;border-radius:4px">
          立即预订 →
        </a>
      </p>
      <p style="color:#999;font-size:12px;margin-top:24px">
        监控时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Alaska Miles Monitor
      </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"✈️ 里程票提醒：发现 {len(results)} 个低价商务舱！"
    msg["From"] = email_cfg["sender"]
    msg["To"] = email_cfg["recipient"]
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(email_cfg["sender"], email_cfg["app_password"])
        server.sendmail(email_cfg["sender"], email_cfg["recipient"], msg.as_string())
    log.info(f"✉️  提醒邮件已发送至 {email_cfg['recipient']}")


# ── 主查询逻辑 ────────────────────────────────────────────
def search_awards(page, route: dict, cfg: dict) -> list[dict]:
    origin = route["origin"]
    destination = route["destination"]
    dates = route["dates"]
    threshold = route.get("threshold_miles", cfg["defaults"]["threshold_miles"])

    # 取日期范围的首尾
    date_start = dates[0]
    date_end = dates[-1]

    log.info(
        f"🔍 查询 {origin}→{destination} {date_start}~{date_end} (Partner Business, Calendar)"
    )
    found = []

    try:
        url = (
            f"https://www.alaskaair.com/search/calendar"
            f"?O={origin}&D={destination}"
            f"&OD={date_start}&A=1&RT=false"
            f"&RequestType=Calendar&ShoppingMethod=onlineaward"
            f"&locale=en-us&FareType=Partner+Business"
        )
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)

        # 等待日历格子加载
        page.wait_for_selector(
            '[class*="calendar"], [class*="Calendar"], table', timeout=60_000
        )
        time.sleep(4)

        found = parse_calendar(page, origin, destination, dates, threshold)
        log.info(f"   完成，命中 {len(found)} 个")

    except PlaywrightTimeoutError:
        log.warning(f"   ⏱ 超时：{origin}→{destination}")
    except Exception as e:
        log.error(f"   ❌ 查询出错：{e}")

    time.sleep(random.uniform(4, 7))
    return found


def parse_calendar(page, origin, destination, dates, threshold) -> list[dict]:
    import re

    found = []
    date_set = set(dates)
    year_month = dates[0][:7]  # "2026-07"

    # 获取页面纯文本
    text = page.inner_text("body")

    # 把所有空行去掉，得到干净的行列表
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    log.info(f"   页面共 {len(lines)} 行文本")

    cells = []
    i = 0
    while i < len(lines):
        # 找纯数字行（1-31，日期）
        if re.match(r"^\d{1,2}$", lines[i]):
            day = int(lines[i])
            if 1 <= day <= 31:
                # 往后找价格：格式是 "175k +" 然后下一行 "$47"
                # 或者合并行 "175k +$47"
                for j in range(i + 1, min(i + 5, len(lines))):
                    line = lines[j]
                    # 合并后面一行看看
                    combined = line
                    if j + 1 < len(lines):
                        combined = line + lines[j + 1]

                    # 匹配 "175k +$47" 或 "175k +" + "$47"
                    m = re.match(r"^([\d.]+)k\s*\+\s*\$([\d.]+)$", combined)
                    if not m:
                        m = re.match(r"^([\d.]+)k\s*\+\s*\$([\d.]+)$", line)
                    if m:
                        cells.append(
                            {"day": day, "miles_k": m.group(1), "cash": m.group(2)}
                        )
                        break
        i += 1

    log.info(f"   找到 {len(cells)} 个日历格子")
    if cells:
        log.info(f"   第一条：{cells[0]}")

    seen = set()
    for cell in cells:
        try:
            full_date = f"{year_month}-{cell['day']:02d}"
            if full_date not in date_set or full_date in seen:
                continue
            seen.add(full_date)

            miles = int(float(cell["miles_k"]) * 1000)
            cash = cell["cash"]
            log.info(f"   {full_date}: {miles:,}里程 +${cash}")

            if miles < threshold:
                log.info(f"   ✅ 命中！{miles:,} < 阈值 {threshold:,}")
                found.append(
                    {
                        "date": full_date,
                        "origin": origin,
                        "destination": destination,
                        "cabin": "Partner Business",
                        "miles": miles,
                        "cash_fee": cash,
                    }
                )
        except Exception as e:
            log.debug(f"   解析格子出错：{e}")

    return found


# ── 登录 ─────────────────────────────────────────────────
def login(page, cfg: dict) -> bool:
    """登录阿拉斯加航空账号（Auth0 + MFA 弹窗版）"""
    creds = cfg["alaska_account"]
    log.info("🔐 正在登录阿拉斯加航空...")

    try:
        page.goto(
            "https://www.alaskaair.com/account/login", wait_until="domcontentloaded"
        )
        time.sleep(4)

        # 填用户名
        page.wait_for_selector('input[name="username"]', timeout=15_000)
        page.fill('input[name="username"]', creds["username"])
        time.sleep(1)

        # 填密码
        page.fill('input[name="password"]', creds["password"])
        time.sleep(1)

        # JS 点击提交（绕过隐藏按钮遮挡）
        page.evaluate("""
            const buttons = Array.from(document.querySelectorAll('button[type="submit"]'));
            const visible = buttons.find(b => !b.hasAttribute('aria-hidden') && b.offsetParent !== null);
            if (visible) visible.click();
            else buttons[buttons.length - 1].click();
        """)
        log.info("   已提交登录表单，等待跳转...")

        # ⭐ 关键：等待 MFA 弹窗的 Skip 按钮 或 主站页面，最多等 30 秒
        try:
            page.wait_for_selector(
                'button:has-text("Skip for now"), a[href*="mileageplan"], [data-testid="header"]',
                timeout=30_000,
            )
        except PlaywrightTimeoutError:
            log.warning("   等待超时，尝试继续...")

        time.sleep(2)
        log.info(f"   当前 URL：{page.url}")

        # 处理 MFA 弹窗
        try:
            skip_btn = page.locator('button:has-text("Skip for now")')
            if skip_btn.is_visible(timeout=3_000):
                log.info("   检测到 MFA 弹窗，自动点击 Skip for now...")
                skip_btn.click()
                # 等待真正跳转离开 auth0
                page.wait_for_url("**/alaskaair.com/**", timeout=20_000)
                time.sleep(3)
                log.info(f"   Skip 后 URL：{page.url}")
        except Exception as e:
            log.info(f"   MFA处理：{e}")
            pass

        # 验证最终是否登录成功（到了主站就算成功）
        final_url = page.url
        if "alaskaair.com" in final_url and "auth0" not in final_url:
            log.info("✅ 登录成功")
            return True
        else:
            # Auth0 页面可能还需要再等一下
            time.sleep(5)
            final_url = page.url
            log.info(f"   最终 URL：{final_url}")
            if "alaskaair.com" in final_url:
                log.info("✅ 登录成功（延迟确认）")
                return True
            log.error("❌ 登录失败")
            try:
                page.screenshot(path="login_failed.png")
            except:
                pass
            return False

    except Exception as e:
        log.error(f"❌ 登录异常：{e}")
        try:
            page.screenshot(path="login_error.png")
        except:
            pass
        return False


# ── 主程序 ────────────────────────────────────────────────
def main():
    cfg = load_config()
    log.info("=" * 55)
    log.info("🛫 Alaska Miles Monitor 启动")
    log.info(f"   监控航线数：{len(cfg['routes'])}")
    log.info("=" * 55)

    all_hits = []

    with sync_playwright() as p:
        import os

        session_path = os.path.join(os.path.dirname(__file__), "session_storage")

        browser = p.chromium.launch(
            executable_path="/Users/lidonghao/Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
            headless=cfg.get("headless", True),
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )

        # 复用已有 session，没有则新建
        context = browser.new_context(
            storage_state=session_path if os.path.exists(session_path) else None,
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        # 检查是否已经登录
        page.goto("https://www.alaskaair.com", wait_until="domcontentloaded")
        time.sleep(2)
        # 检查 URL 或页面内容判断是否已登录
        current_url = page.url
        page_text = page.inner_text("body")
        already_logged_in = (
            "sign in" not in page_text.lower()
            and "log in" not in page_text.lower()
            and os.path.exists(session_path)
        )
        log.info(
            f"   Session文件存在：{os.path.exists(session_path)}，判断已登录：{already_logged_in}"
        )

        if already_logged_in:
            log.info("✅ 使用已保存的登录状态，跳过登录")
        else:
            log.info("🔑 未检测到登录状态，重新登录...")
            if not login(page, cfg):
                log.error("登录失败，程序退出")
                browser.close()
                return
            # 保存 session
            context.storage_state(path=session_path)
            log.info(f"💾 登录状态已保存")

        # 逐条查询航线
        for route in cfg["routes"]:
            hits = search_awards(page, route, cfg)
            all_hits.extend(hits)
            time.sleep(random.uniform(5, 10))  # 航线间间隔

        browser.close()

    # 发送提醒
    if all_hits:
        log.info(f"\n🎯 共发现 {len(all_hits)} 个低价里程票，正在发送邮件...")
        send_alert(cfg, all_hits)
    else:
        log.info("\n😴 本次未发现低于阈值的里程票")

    log.info("✅ 本次监控完成\n")


if __name__ == "__main__":
    import time as _time

    while True:
        try:
            main()
        except Exception as e:
            log.error(f"主程序异常：{e}")
        log.info("⏳ 等待10秒后再次查询...")
        _time.sleep(10)
