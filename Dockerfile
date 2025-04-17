FROM python:3.10-slim

WORKDIR /app

COPY . .

# Install dependencies and update system packages
RUN apt-get update && apt-get install -y gcc libpq-dev && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
