FROM mambaorg/micromamba:1.3.1-alpine
LABEL maintainer="Thomas Unterholzner <thomas.unterholzner@geo.tuwien.ac.at>"

USER root

RUN apk update && \
    apk upgrade && \
    apk add --no-cache \
        git \
        build-base \
        libbsd \
        libbsd-dev \
        libtiff \
        libtiff-dev \
        lftp

WORKDIR /app

COPY . /app

ARG MAMBA_DOCKERFILE_ACTIVATE=1
ARG PIP_USE_PEP517=1

RUN micromamba install -y -n base -c conda-forge python=3.12
RUN micromamba install -y -n base -f /app/environment.yml && pip install /app/.

RUN micromamba clean --all --yes

# Clean up the src code, as it is installed now
RUN rm -rf /app

ENTRYPOINT ["/usr/local/bin/_entrypoint.sh"]