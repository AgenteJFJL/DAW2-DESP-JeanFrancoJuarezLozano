FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Usuario sin privilegios: el proceso NO corre como root (Tarea 9, pregunta 1)
RUN useradd --uid 1000 --create-home app \
    && mkdir -p /data/media \
    && chown -R app:app /data /app

COPY --chown=app:app . .

USER app
EXPOSE 5000

CMD ["gunicorn", "--preload", "--workers", "2", "--bind", "0.0.0.0:5000", \
     "--access-logfile", "-", "--error-logfile", "-", "app:app"]
