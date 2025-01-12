FROM python:3.10.13-alpine3.18

WORKDIR /usr/src

RUN pip install poetry

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-dev

COPY app/ app/

ENV PYTHONPATH /usr/src

CMD ["python", "app/main.py"]
