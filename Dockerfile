FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# state.json และ session จะถูก mount จาก host
VOLUME ["/app/data"]

ENV STATE_FILE=/app/data/state.json
ENV TELEGRAM_SESSION=/app/data/telegram_session

CMD ["python", "main.py"]
