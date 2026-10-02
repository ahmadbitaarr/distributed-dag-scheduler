# On-demand Linux harness/client container (architecture §15): JDK 21 + Maven,
# Python + pinned pytest, and ffmpeg/ffprobe. Run it with the repository mounted
# at /work (see deploy/harness/run.sh) so builds, tests and evidence use the
# checked-out source.
FROM maven:3.9.9-eclipse-temurin-21
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt
ENV PATH=/opt/venv/bin:$PATH
WORKDIR /work
