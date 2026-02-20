FROM python:3.11-slim

WORKDIR /workspace

ENV PYTHONPATH=/workspace

COPY requirements.txt .
RUN apt-get update && pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["uvicorn", "app.main:app"]
CMD ["--host", "0.0.0.0", "--port", "8000"]