FROM python:3.11-slim

WORKDIR /app

# Install cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY entrypoint.sh .

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# state.json และ session จะถูก mount จาก host
VOLUME ["/app/data"]

ENV STATE_FILE=/app/data/state.json
ENV TELEGRAM_SESSION=/app/data/telegram_session

ENTRYPOINT ["/app/entrypoint.sh"]
