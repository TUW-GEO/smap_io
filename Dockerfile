FROM mambaorg/micromamba:1.3.1-alpine

LABEL maintainer="Thomas Unterholzner <thomas.unterholzner@geo.tuwien.ac.at>"

USER root

# Install system dependencies
RUN apk update && apk upgrade && \
    apk add --no-cache \
        git \
        build-base \
        libbsd \
        tiff-dev \
        lftp

WORKDIR /app

# Copy project files
COPY . /app

# ARGs for micromamba environment activation and pip
ARG MAMBA_DOCKERFILE_ACTIVATE=1
ARG PIP_USE_PEP517=1

# Install Python and dependencies
RUN micromamba install -y -n base -c conda-forge python=3.12 && \
    micromamba install -y -n base -f /app/environment.yml && \
    pip install /app/. && \
    micromamba clean --all --yes

# Remove source code as it is installed
RUN rm -rf /app

# Entrypoint for container
ENTRYPOINT ["/usr/local/bin/_entrypoint.sh"]
