FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies first (cached layer), then the project itself.
COPY pyproject.toml uv.lock LICENSE README.md ./
RUN uv sync --frozen --no-install-project --extra api --no-dev

COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations
RUN uv sync --frozen --extra api --no-dev

COPY docker/api-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
CMD ["/entrypoint.sh"]
