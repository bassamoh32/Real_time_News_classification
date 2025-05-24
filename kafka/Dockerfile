FROM python:3.11-slim

WORKDIR /app

COPY ./kafka .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

CMD ["python", "kafka/producer.py"]