# build from repo root: docker build -f worker/Dockerfile -t cmd-worker:1.0 .
FROM python:3.11-slim
WORKDIR /app
COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY worker/ /app/
COPY prompts/ /app/prompts/
ENV PROMPT_PATH=/app/prompts/teacher_prompt.txt
CMD ["python", "worker.py"]
