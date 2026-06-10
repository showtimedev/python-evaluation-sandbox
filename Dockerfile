# Pinned base image (digest-pinnable in CI). Python 3.12 matches requires-python.
FROM python:3.12.4-slim-bookworm

# Fail fast, no .pyc, unbuffered logs - standard for reproducible CI containers.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Isolated virtual environment so we never touch the system interpreter.
RUN python -m venv "$VIRTUAL_ENV"

# Copy only what is needed to resolve dependencies first, to maximise layer cache.
COPY pyproject.toml README.md ./
COPY src ./src

# Install the project plus its dev (test) extras into the venv.
RUN pip install --upgrade pip==24.0 \
    && pip install ".[dev]"

# Now bring in the tests.
COPY tests ./tests

# Default command runs the suite. The container "passing" == tests green.
CMD ["pytest"]
