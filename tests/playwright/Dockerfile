# Playwright E2E test-runner image.
#
# Build context: the repository root (so all test files and the component
# source are available inside the container).
FROM python:3.12-slim

WORKDIR /app

# System packages needed by Playwright's bundled Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (test suite)
COPY tests/playwright/requirements.txt ./playwright-requirements.txt
RUN pip install --no-cache-dir -r playwright-requirements.txt && \
    playwright install chromium && \
    playwright install-deps chromium

# Copy the full repository so the component source and all test files
# are available at /app (component root) and /app/tests/playwright/.
COPY . /app

COPY tests/playwright/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
