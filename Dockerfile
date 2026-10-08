# Test runner image: Python + Playwright browsers + the suite.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Which browsers to bake in. Default = all three; use --build-arg BROWSERS=chromium for a smaller image.
ARG BROWSERS="chromium firefox webkit"

COPY requirements.txt .
RUN pip install -r requirements.txt \
 && playwright install --with-deps ${BROWSERS}

COPY . .

# Runs pytest, then generates the AI report, and returns pytest's exit code.
# Override the test selection with:  -e PYTEST_ARGS='-m smoke --browser firefox'
CMD ["python", "-m", "utils.run_suite"]
