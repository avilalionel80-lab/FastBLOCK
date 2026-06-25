FROM python:3.12-slim AS builder

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --prefix=/install -r requirements.txt

FROM gcr.io/distroless/python3-debian12

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder /install /usr/local
COPY main.py .
COPY app ./app

USER nonroot:nonroot

EXPOSE 8000

CMD ["-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
