FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
LABEL authors="jfeil"

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install  -y --no-install-recommends libreoffice-impress poppler-utils

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY main.py /app
COPY uv.lock /app
COPY .python-version /app
COPY pyproject.toml /app
COPY src /app/src
COPY pages /app/pages
COPY assets /app/assets

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

EXPOSE 8080
CMD ["gunicorn", "main:server", "-b", ":8080"]