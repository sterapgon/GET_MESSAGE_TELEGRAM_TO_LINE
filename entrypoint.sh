#!/bin/bash

# สร้าง log directory ถ้ายังไม่มี
mkdir -p /app/data/logs

# Setup crontab
# 06:15 ทุกวัน
CRON_SCHEDULE="15 6 * * *"
CRON_COMMAND="cd /app && python main.py >> /app/data/logs/cron.log 2>&1"

# เขียน crontab
echo "$CRON_SCHEDULE $CRON_COMMAND" | crontab -

echo "✓ Cron job installed: $CRON_SCHEDULE"
echo "✓ Log file: /app/data/logs/cron.log"

# Start cron daemon ใน foreground
exec cron -f
