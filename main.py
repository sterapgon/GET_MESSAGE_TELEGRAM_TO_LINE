"""
Telegram Bot → LINE forwarder
Reads messages posted by a specific Telegram bot and forwards them to LINE as-is.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone, time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import PeerChannel, User

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]           # username, @channel, or numeric ID
BOT_USERNAME = os.environ["TELEGRAM_BOT_USERNAME"]  # e.g. "my_bot" (without @)

LINE_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_TARGET = os.environ["LINE_TARGET_ID"]           # userId, groupId, or roomId

SESSION_FILE = os.environ.get("TELEGRAM_SESSION", "telegram_session")
STATE_FILE = Path(os.environ.get("STATE_FILE", "state.json"))

DRY_RUN = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")

# จำนวนข้อความสูงสุดต่อรอบ (ป้องกันเกินโควต้า LINE)
# ตั้งเป็น 0 เพื่อไม่จำกัด
MAX_PER_RUN = int(os.environ.get("MAX_MESSAGES_PER_RUN", "50"))

# หน่วง delay ระหว่างแต่ละข้อความ (วินาที) เพื่อหลีกเลี่ยง LINE 429
LINE_SEND_DELAY = float(os.environ.get("LINE_SEND_DELAY", "1.0"))

# กรองเฉพาะข้อความในช่วงเวลาที่กำหนด (HH:MM) — เว้นว่างเพื่อไม่กรอง
_TW_TZ   = ZoneInfo(os.environ.get("TIME_WINDOW_TZ", "Asia/Bangkok"))
_TW_RAW_START = os.environ.get("TIME_WINDOW_START", "").strip()
_TW_RAW_END   = os.environ.get("TIME_WINDOW_END",   "").strip()

def _parse_hhmm(s: str) -> dtime | None:
    if not s:
        return None
    h, m = s.split(":")
    return dtime(int(h), int(m))

TIME_WINDOW_START: dtime | None = _parse_hhmm(_TW_RAW_START)
TIME_WINDOW_END:   dtime | None = _parse_hhmm(_TW_RAW_END)


def in_time_window(msg_date: datetime, today: "datetime.date") -> bool:
    """Return True if message is from today (Bangkok) and within [start, end] window."""
    local_dt = msg_date.astimezone(_TW_TZ)
    # ต้องเป็นวันเดียวกับที่รัน script เท่านั้น
    if local_dt.date() != today:
        return False
    if TIME_WINDOW_START is None and TIME_WINDOW_END is None:
        return True
    local_time = local_dt.time().replace(second=0, microsecond=0)
    if TIME_WINDOW_START and local_time < TIME_WINDOW_START:
        return False
    if TIME_WINDOW_END and local_time > TIME_WINDOW_END:
        return False
    return True

# ── State helpers ─────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"last_message_id": 0}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── LINE sender ───────────────────────────────────────────────────────────────

def send_to_line(text: str) -> None:
    """Send a single text message to LINE. Raises on non-2xx response."""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": LINE_TARGET,
        "messages": [{"type": "text", "text": text}],
    }
    resp = httpx.post(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()


# ── Main logic ────────────────────────────────────────────────────────────────

async def run(dry_run: bool = DRY_RUN) -> None:
    state = load_state()
    last_id: int = state["last_message_id"]

    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting  last_id={last_id}  dry_run={dry_run}  max_per_run={MAX_PER_RUN or 'unlimited'}")

    async with TelegramClient(SESSION_FILE, API_ID, API_HASH) as client:
        # Resolve the chat — numeric IDs like -1001234567890 need PeerChannel
        chat_input = CHAT_ID.strip()
        if chat_input.lstrip("-").isdigit():
            raw_id = int(chat_input)
            # Supergroup/channel IDs are stored as -100XXXXXXXXXX; strip the prefix
            if str(abs(raw_id)).startswith("100"):
                raw_id = int(str(abs(raw_id))[3:])
            chat = await client.get_entity(PeerChannel(raw_id))
        else:
            chat = await client.get_entity(chat_input)

        # Resolve the bot entity to get its numeric ID
        bot_entity = await client.get_entity(BOT_USERNAME)
        bot_id: int = bot_entity.id

        today_bkk = datetime.now(_TW_TZ).date()

        print(f"Watching chat: {getattr(chat, 'title', None) or getattr(chat, 'username', chat.id)}")
        print(f"Filtering bot: @{BOT_USERNAME} (id={bot_id})")
        print(f"Today (Bangkok): {today_bkk}")

        # Fetch messages newer than last_id in chronological order
        new_messages = []
        async for msg in client.iter_messages(chat, min_id=last_id, reverse=True):
            if not msg.text:
                continue
            sender = await msg.get_sender()
            if not isinstance(sender, User):
                continue
            if sender.id != bot_id:
                continue
            if not in_time_window(msg.date, today_bkk):
                continue
            new_messages.append(msg)

        if not new_messages:
            print("No new bot messages. Nothing to do.")
            return

        total_found = len(new_messages)
        if MAX_PER_RUN and total_found > MAX_PER_RUN:
            print(f"Found {total_found} message(s) — capping to {MAX_PER_RUN} this run (set MAX_MESSAGES_PER_RUN=0 to disable).")
            new_messages = new_messages[:MAX_PER_RUN]
        else:
            print(f"Found {total_found} new message(s) to forward.")

        sent_up_to_id = last_id
        for i, msg in enumerate(new_messages):
            ts = msg.date.strftime("%Y-%m-%d %H:%M UTC")
            preview = msg.text[:60].replace("\n", "↵")
            print(f"  [{i+1}/{len(new_messages)}] msg_id={msg.id}  [{ts}]  \"{preview}{'…' if len(msg.text) > 60 else ''}\"")

            if dry_run:
                print("  → [DRY RUN] Would send to LINE (skipped)")
            else:
                send_to_line(msg.text)
                print(f"  → Sent to LINE ✓")
                # บันทึก state ทันทีหลังส่งสำเร็จแต่ละข้อความ
                state["last_message_id"] = msg.id
                state["last_run"] = datetime.now(timezone.utc).isoformat()
                save_state(state)
                # หน่วงก่อนส่งข้อความถัดไป
                if i < len(new_messages) - 1:
                    time.sleep(LINE_SEND_DELAY)

            sent_up_to_id = msg.id

        if dry_run:
            print("[DRY RUN] State not updated.")
        else:
            remaining = total_found - len(new_messages)
            if remaining:
                print(f"\nDone. {remaining} message(s) remaining — will be sent on next run.")
            else:
                print(f"\nDone. All messages forwarded. last_message_id={sent_up_to_id}")


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
