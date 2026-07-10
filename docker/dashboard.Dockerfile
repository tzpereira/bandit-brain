FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock LICENSE README.md ./
RUN uv sync --frozen --no-install-project --extra dashboard --no-dev

COPY src ./src
RUN uv sync --frozen --extra dashboard --no-dev

COPY dashboard ./dashboard
COPY public ./public

EXPOSE 8501
CMD ["uv", "run", "--frozen", "--no-dev", "--extra", "dashboard", "streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
