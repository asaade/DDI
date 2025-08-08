# Dockerfile
FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /usr/src/app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
