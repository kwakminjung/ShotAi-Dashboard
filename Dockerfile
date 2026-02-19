FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/
RUN apt-get update && pip install --no-cache-dir -r requirements.txt

COPY . /app/

ENTRYPOINT ["uvicorn", "main:app"]
CMD ["--host", "0.0.0.0", "--port", "8000"]