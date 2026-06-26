# Telegram Bot → LINE Forwarder
สร้าง: 2026-06-26

อ่านข้อความที่บอท Telegram โพสต์ แล้วส่งต่อไปยัง LINE ทุกวัน

---

## วิธีติดตั้ง

### 1. ติดตั้ง Python dependencies

```bash
pip install -r requirements.txt
```

### 2. ตั้งค่า credentials

```bash
cp .env.example .env
# แก้ไขค่าใน .env ให้ครบ
```

ค่าที่ต้องกรอก:

| ตัวแปร | หาได้จากไหน |
|---|---|
| `TELEGRAM_API_ID` | [my.telegram.org](https://my.telegram.org) → API development tools |
| `TELEGRAM_API_HASH` | เดียวกัน |
| `TELEGRAM_CHAT_ID` | `@username` ของช่อง หรือ numeric ID เช่น `-100123456789` |
| `TELEGRAM_BOT_USERNAME` | ชื่อบอทไม่มี @ เช่น `my_news_bot` |
| `LINE_CHANNEL_ACCESS_TOKEN` | [LINE Developers Console](https://developers.line.biz) → Messaging API → Channel access token |
| `LINE_TARGET_ID` | userId/groupId ที่ต้องการส่ง (ดูวิธีข้างล่าง) |

**หา LINE_TARGET_ID:**
- เปิด Webhook ใน LINE Console → ส่งข้อความหาบอท → log ดู `event.source.userId`
- หรือใช้ curl: `curl https://api.line.me/v2/bot/profile -H "Authorization: Bearer <TOKEN>"`

### 3. Login Telegram ครั้งแรก (ทำครั้งเดียว)

```bash
python main.py
```

Telethon จะถามหมายเลขโทรศัพท์และ OTP → หลังจากนั้นจะสร้างไฟล์ `telegram_session.session` ไว้ใช้ต่อ

---

## การรัน

### รันปกติ

```bash
python main.py
```

### Dry-run (ดูว่าจะส่งอะไร โดยไม่ส่งจริง)

```bash
DRY_RUN=1 python main.py
# Windows PowerShell:
$env:DRY_RUN=1; python main.py
```

### รีเซ็ต state (เริ่มดึงจากต้น)

```bash
del state.json   # Windows
rm state.json    # Linux/Mac
```

---

## ตั้งเวลารันอัตโนมัติ (Windows Task Scheduler)

1. เปิด **Task Scheduler** → Create Basic Task
2. Trigger: Daily → เวลาที่ต้องการ เช่น 08:00
3. Action: Start a program
   - Program: `python`
   - Arguments: `main.py`
   - Start in: `D:\Apps\mini_get_telegram_message`
4. ใน General tab → ติ๊ก "Run whether user is logged on or not"

**หรือใช้ cron บน Linux/Mac:**

```cron
0 8 * * * cd /path/to/mini_get_telegram_message && python main.py >> /var/log/tg2line.log 2>&1
```

---

## โครงสร้างไฟล์

```
.
├── main.py           # script หลัก
├── .env              # credentials (ห้าม commit)
├── .env.example      # template
├── requirements.txt
├── state.json        # เก็บ last_message_id (auto-created)
└── telegram_session.session  # Telethon session (auto-created, ห้าม commit)
```

---

## ข้อจำกัด

- **Telethon ต้องการ user account** (ไม่ใช่ bot token) เพื่ออ่านประวัติข้อความย้อนหลัง
- LINE Messaging API push message ต้องการ plan ที่รองรับ push (Free plan มีโควต้า 200 msg/เดือน)
- LINE รองรับ Unicode และ line break ตามปกติ แต่ไม่รองรับ Markdown/HTML
- ถ้าบอทโพสต์รูปหรือไฟล์ โปรแกรมจะข้ามไป (ส่งเฉพาะ text)
