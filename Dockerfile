# Image with the smap_io package.
# Usage, e.g.: docker run --rm -v /data:/data <image> smap_l3 update_img /data/smap_l3
# Earthdata credentials for downloads are passed with --username / --password
# (or a ~/.netrc file).
ARG PYTHON_VERSION=3.14

# Build the wheel in a separate stage, git is needed to derive the version
# (setuptools_scm), but is not part of the final image.
FROM python:${PYTHON_VERSION}-slim AS build
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY . .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels .

FROM python:${PYTHON_VERSION}-slim
LABEL org.opencontainers.image.source="https://github.com/TUW-GEO/smap_io" \
      org.opencontainers.image.description="SMAP soil moisture data download, readers and time series conversion" \
      org.opencontainers.image.licenses="MIT"
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

CMD ["smap_l3", "--help"]
