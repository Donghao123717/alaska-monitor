# ✈️ Alaska Airlines Miles Monitor

> 自动监控阿拉斯加航空里程票价格，低于阈值时发送邮件提醒。

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![Playwright](https://img.shields.io/badge/Playwright-Latest-green?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

## 功能特点

- 🔍 **自动查询** — 使用 Playwright 模拟浏览器，登录你的 MileagePlan 账号查询里程票
- 📅 **日历视图** — 一次请求获取整月 Partner Business 舱位价格，高效快速
- 📧 **邮件提醒** — 发现低价票时自动发送 Gmail 提醒邮件
- 💾 **Session 保持** — 保存登录状态，避免频繁登录触发验证
- 🔄 **持续监控** — 后台循环运行，无需手动干预
- ⚙️ **灵活配置** — 通过 `config.yaml` 管理所有航线、日期、阈值

---

## 快速开始

### 1. 安装依赖

```bash
pip3 install playwright pyyaml
python3 -m playwright install chromium
```

### 2. 配置 config.yaml

复制模板并填入你的信息：

```yaml
alaska_account:
  username: "YOUR_MILEAGEPLAN_NUMBER"
  password: "YOUR_PASSWORD"

email:
  sender: "YOUR_GMAIL@gmail.com"
  app_password: "YOUR_GMAIL_APP_PASSWORD"
  recipient: "YOUR_GMAIL@gmail.com"

defaults:
  threshold_miles: 85000
  cabin: "business"

headless: true

routes:
  - origin: "TPE"
    destination: "SEA"
    threshold_miles: 85000
    dates: ["2026-07-07","2026-07-08","2026-07-09","2026-07-10"]
```

> **Gmail App Password 获取方式：**
> Google 账号 → 安全性 → 两步验证 → 应用专用密码 → 生成

### 3. 测试运行

```bash
python3 monitor.py
```

### 4. 后台持续运行

```bash
nohup python3 monitor.py > /dev/null 2>&1 &
echo $! > monitor.pid
```

**停止：**
```bash
kill $(cat monitor.pid)
```

**查看日志：**
```bash
tail -f monitor.log
```

---

## 支持航线

脚本支持所有阿拉斯加航空里程票航线，在 `config.yaml` 的 `routes` 里添加即可。常用出发地：

| 代码 | 城市 |
|------|------|
| TPE | 台北桃园 |
| NRT | 东京成田 |
| HND | 东京羽田 |
| ICN | 首尔仁川 |

| 代码 | 目的地 |
|------|--------|
| SEA | 西雅图 |
| LAX | 洛杉矶 |
| SFO | 旧金山 |
| PHX | 凤凰城 |

---

## 邮件提醒示例

触发后你会收到如下提醒：

```
✈️ 里程票提醒：发现 3 个低价商务舱！

日期        航线          舱位              里程        税费
2026-07-07  TPE → SEA    Partner Business  75,000     $47
2026-07-08  TPE → SEA    Partner Business  75,000     $47
2026-07-09  NRT → LAX    Partner Business  80,000     $45
```

---

## 文件说明

```
alaska-monitor/
├── monitor.py            # 主程序
├── debug_selectors.py    # 调试工具
├── config.yaml           # 配置文件（填入你的信息）
├── install.sh            # 一键安装
└── README.md
```

---

## 注意事项

- 本脚本仅用于个人账号的自动化查询，请勿滥用
- 建议查询间隔不少于 5 分钟，避免触发网站反爬机制
- Session 一般可保持数天，失效后会自动重新登录
- Mac 睡眠时脚本仍会继续运行

---

## License

MIT
