FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

WORKDIR /opt/bot

RUN pip install --no-cache-dir "poetry==2.5.1"

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root

COPY app/ app/

RUN useradd --create-home --uid 10001 bot
USER bot

ENV PATH="/opt/bot/.venv/bin:$PATH"
CMD ["python", "-m", "app.main"]
