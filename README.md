# ✈️ Alaska Airlines 里程票监控脚本

自动监控阿拉斯加航空里程票商务舱价格，低于阈值时发邮件提醒。

---

## 📁 文件说明

```
alaska_monitor/
├── monitor.py           # 主程序
├── debug_selectors.py   # 调试工具（选择器失效时用）
├── config.yaml          # 所有配置（账号/航线/阈值）
├── install.sh           # 一键安装
└── setup_cron.sh        # 设置定时任务
```

---

## 🚀 快速开始

### 第一步：安装依赖

```bash
cd alaska_monitor
bash install.sh
```

### 第二步：配置 config.yaml

```yaml
alaska_account:
  username: "你的 MileagePlan 号或邮箱"
  password: "你的密码"

email:
  sender: "你的Gmail@gmail.com"
  app_password: "Gmail App 专用密码"   # 见下方说明
  recipient: "收提醒的邮箱"

routes:
  - origin: "SEA"
    destination: "NRT"
    cabin: "business"
    threshold_miles: 55000    # 低于 5.5 万里程触发提醒
    dates:
      - "2025-08-01"
      - "2025-08-02"
```

### 第三步：获取 Gmail App Password

> Google 账号 → 安全性 → 两步验证（需先开启）→ 应用专用密码 → 生成

生成后是 16 位，填入 config.yaml 的 `app_password`。

### 第四步：测试运行

```bash
python3 monitor.py
```

首次建议把 `headless: true` 改为 `headless: false`，可以看到浏览器操作过程。

### 第五步：设置定时任务（每小时自动运行）

```bash
bash setup_cron.sh
```

---

## 🐞 调试选择器

阿拉斯加航空网站改版后，如果脚本无法正确抓取数据，运行调试工具：

```bash
python3 debug_selectors.py
```

会生成截图 + 打印所有包含 "miles" 的 HTML 元素，帮助找到新的选择器。  
然后更新 `monitor.py` 中 `parse_flight_card()` 函数里的选择器即可。

---

## ⚠️ 注意事项

| 事项 | 说明 |
|------|------|
| 查询频率 | 建议每小时一次，避免触发反爬 |
| Mac 睡眠 | 睡眠时 cron 不运行，监控期间保持唤醒 |
| 登录失效 | 账号密码变更后更新 config.yaml |
| 网站改版 | 用 debug_selectors.py 重新找选择器 |
| 两步验证 | 如账号开启了 2FA，需先在浏览器手动处理一次 |

---

## 📬 邮件示例

触发后你会收到如下提醒邮件：

```
✈️ 里程票提醒：发现 2 个低价商务舱！

日期        航线          舱位      里程        税费   余座
2025-08-01  SEA → NRT    Business  52,000 里程  $56    3座
2025-08-02  SEA → NRT    Business  48,500 里程  $56    1座
```
