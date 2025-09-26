FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app/src
COPY src/ /app/src
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "/app/src/store_manager.py"]