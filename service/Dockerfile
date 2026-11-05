# build from repo root:  docker build -f service/Dockerfile -t cmd-parser:1.0 .
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY service/requirements.txt .
RUN pip install -r requirements.txt && rm -rf /root/.cache
COPY service/app.py service/schema.json /app/
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
