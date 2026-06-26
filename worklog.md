# Worklog — Telegram Bot → LINE Forwarder

## 2026-06-26 — สร้าง project ครั้งแรก

**สิ่งที่สร้าง:**
- `main.py` — script หลัก (Telethon + httpx + dotenv)
- `.env.example` — template credentials
- `requirements.txt` — dependencies: telethon, httpx, python-dotenv
- `README.md` — setup instructions + scheduling guide
- `.gitignore` — ป้องกัน .env / session file หลุด git

## 2026-06-26 — เพิ่ม time window filter + Docker

**เพิ่ม:**
- `TIME_WINDOW_START` / `TIME_WINDOW_END` กรองเฉพาะข้อความในช่วงเวลา (HH:MM, Asia/Bangkok)
- date filter — เฉพาะข้อความของวันที่รัน script เท่านั้น ไม่ดึงย้อนหลัง
- `MAX_MESSAGES_PER_RUN` จำกัดจำนวนต่อรอบ (default 50) ป้องกันเกินโควต้า LINE
- `LINE_SEND_DELAY` หน่วง delay ระหว่างข้อความ ป้องกัน 429
- บันทึก state ทีละข้อความ (ไม่ใช่ batch) เพื่อ resume ได้ถ้าพังกลางคัน
- Dockerfile + docker-compose.yml พร้อม mount `./data` สำหรับ session + state
- `data/` folder สำหรับ volume

---

**การออกแบบ:**
- ใช้ Telethon (MTProto user session) แทน Bot API เพราะ Bot API อ่านประวัติย้อนหลังไม่ได้
- `iter_messages(min_id=last_id, reverse=True)` ดึงเฉพาะข้อความใหม่กว่า last run เรียงจากเก่าไปใหม่
- กรองด้วย `sender.id == bot_id` (resolve จาก `TELEGRAM_BOT_USERNAME`)
- ส่ง LINE ด้วย httpx push message API ทีละข้อความ
- บันทึก `last_message_id` ใน `state.json` หลังส่งสำเร็จแต่ละข้อความ
- `DRY_RUN=1` ทำให้พิมพ์แต่ไม่ส่งจริงและไม่อัปเดต state
