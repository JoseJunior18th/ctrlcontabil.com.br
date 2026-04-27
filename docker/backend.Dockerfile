FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY backend/pyproject.toml ./
COPY backend/app ./app

RUN python -m pip install --no-cache-dir --upgrade pip \
  && python -m pip install --no-cache-dir .

EXPOSE 5075

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5075", "--proxy-headers", "--forwarded-allow-ips", "*"]
