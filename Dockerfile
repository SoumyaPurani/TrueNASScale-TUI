FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.7.2 /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    TERM=xterm-256color

RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid app --create-home app

WORKDIR /app
RUN chown app:app /app

USER app

COPY --chown=app:app pyproject.toml uv.lock .python-version LICENSE README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=app:app src/ src/
RUN uv sync --frozen --no-dev

ENTRYPOINT ["uv", "run", "--no-sync", "truenasscale-tui"]
