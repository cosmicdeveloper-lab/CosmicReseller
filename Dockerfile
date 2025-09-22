# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ca-certificates xvfb xauth \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app

# Copy metadata AND source before install (editable install needs /app/src)
COPY pyproject.toml README.md /app/
COPY src/ /app/src/

# Install deps & your package (editable)
RUN pip install --upgrade pip && pip install -e .

# Playwright system deps + Firefox
RUN python -m playwright install-deps && \
    python -m playwright install firefox

# Non-root user
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["xvfb-run", "-s", "-screen 0 1920x1080x24", "python", "-m", "src.cosmicreseller.main"]
