# Used by CI and local quick smoke. Editable install for development: see docs/LOCAL_HELM_QUICKSTART.md
FROM python:3.11-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY CancerGenomicsSuite ./CancerGenomicsSuite

# Optional extras: add [ngs] for pysam on Linux (native wheels / build)
RUN python -m pip install --upgrade pip && \
    pip install -e ".[dev,test,ngs]"

USER nobody
CMD ["python", "-c", "import CancerGenomicsSuite; print('CancerGenomicsSuite import ok')"]
