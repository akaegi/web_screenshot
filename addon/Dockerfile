FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1

# The Node.js driver bundled with Playwright needs libatomic, which the slim image lacks
# ("libatomic.so.1: cannot open shared object file").
RUN apt-get update \
    && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# No local browser: rendering happens on Browserless, so only the
# Playwright client library is needed.
RUN pip install --no-cache-dir playwright

COPY screenshot.py run.py /app/

CMD ["python3", "/app/run.py"]
