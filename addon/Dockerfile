FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1

# No local browser: rendering happens on Browserless, so only the
# Playwright client library is needed.
RUN pip install --no-cache-dir playwright

COPY screenshot.py run.py /app/

CMD ["python3", "/app/run.py"]
