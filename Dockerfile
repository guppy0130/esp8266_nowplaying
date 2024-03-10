FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

EXPOSE 3000

RUN apt update \
  && DEBIAN_FRONTEND=noninteractive apt install -y git \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY README.md .
COPY server.py .

RUN --mount=source=.git,target=.git,type=bind \
  ls -lah

# mount in local .git for setuptools_scm:
# https://github.com/pypa/setuptools_scm/issues/77#issuecomment-844927695
RUN --mount=source=.git,target=.git,type=bind \
  pip install --no-cache-dir --no-color .


CMD ["hypercorn", "server:app", "--bind", "0.0.0.0:3000", "--access-logfile", "-", "--log-file", "-"]
