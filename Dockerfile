FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir --upgrade 'pip>=26.2'
# Install the exact versions resolved in requirements.lock (reproducible builds).
RUN pip install --no-cache-dir -r requirements.lock

COPY . .

RUN mkdir -p /app/uploads/avatars /app/secrets
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
