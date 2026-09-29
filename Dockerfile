# Evactive - container image for Hugging Face Spaces (Docker SDK) or any Docker host.
# The dashboard is pre-built in frontend/dist, so only Python is needed at runtime.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860

# Hugging Face Spaces run containers as user 1000
RUN useradd -m -u 1000 user
WORKDIR /home/user/app

COPY --chown=user backend/requirements.txt backend/requirements.txt
RUN pip install --upgrade pip && pip install -r backend/requirements.txt

COPY --chown=user backend backend
COPY --chown=user frontend/dist frontend/dist

USER user
WORKDIR /home/user/app/backend
EXPOSE 7860

# HF_TOKEN (and optionally HF_MODEL) come from the host's secrets / environment
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860} --proxy-headers --forwarded-allow-ips='*'"]
