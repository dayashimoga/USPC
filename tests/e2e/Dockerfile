# Playwright Browser E2E Test Container Harness for USPC
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -e ".[dev]" pytest-playwright

CMD ["pytest", "tests/e2e/", "-v"]
