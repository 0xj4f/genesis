FROM python:3.13-slim-trixie AS build

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir --upgrade 'pip>=26.2'
# Install the exact versions resolved in requirements.lock (reproducible builds).
RUN pip install --no-cache-dir --target=/opt/python-deps -r requirements.lock

RUN mkdir -p /runtime/uploads/avatars /runtime/secrets /runtime/log \
    && chown -R 65532:65532 /runtime && chmod 0750 /runtime/log /runtime/secrets

# No shell, package manager, compiler or debug tools in the runtime image.
FROM gcr.io/distroless/python3-debian13:nonroot
WORKDIR /app
ENV PYTHONPATH=/opt/python-deps:/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY --from=build /opt/python-deps /opt/python-deps
COPY --from=build --chown=65532:65532 /runtime/uploads /app/uploads
COPY --from=build --chown=65532:65532 /runtime/secrets /app/secrets
COPY --from=build --chown=65532:65532 /runtime/log /var/log
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
USER 65532:65532

EXPOSE 8000

ENTRYPOINT ["/usr/bin/python3", "-m", "app.entrypoint"]
