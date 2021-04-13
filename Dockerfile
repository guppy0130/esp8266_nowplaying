FROM python:3-slim

WORKDIR /usr/src/app

COPY server.py ./
COPY requirements.txt ./

RUN pip install --no-cache-dir --upgrade pip && \
  pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:80", "-w", "4", "server:app"]
