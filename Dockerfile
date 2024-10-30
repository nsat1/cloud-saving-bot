FROM python:3.10.13-alpine3.18

WORKDIR /usr/src

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

ENV PYTHONPATH /usr/src

CMD ["python", "app/main.py"]
