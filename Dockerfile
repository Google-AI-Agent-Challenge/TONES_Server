# Build stage
FROM python:3.12-slim as builder

WORKDIR /workspace

# C/Rust 컴파일러가 완전히 배제되었으므로 apt-get 단계 극단적 슬림화
RUN apt-get update && rm -rf /var/lib/apt/lists/*

# 가상환경(venv) 생성 및 활용
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Run stage
FROM python:3.12-slim as runner

WORKDIR /workspace

# 빌드 스테이지의 가상환경 전체 복사
COPY --from=builder /opt/venv /opt/venv
COPY . .

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

