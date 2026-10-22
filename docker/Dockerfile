# SoapFL + Defects4J 1.4.0 + Java 8 + Python 3.11, talking to Ollama running on the HOST.
# UNTESTED by the author (no Docker in the authoring sandbox). The Defects4J step downloads several GB.
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8
# retry flaky mirror downloads (e.g. the deadsnakes PPA sometimes answers 503)
RUN echo 'Acquire::Retries "8";' > /etc/apt/apt.conf.d/80retries

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl wget git subversion unzip zip perl cpanminus build-essential \
      openjdk-8-jdk software-properties-common gnupg \
 && add-apt-repository -y ppa:deadsnakes/ppa \
 && apt-get update && apt-get install -y --no-install-recommends \
      python3.11 python3.11-venv python3.11-dev \
 && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64

# Defects4J 1.4.0
# NOTE: the v1.4.0 init.sh downloads the bug repositories from people.cs.umass.edu, which now returns 404, and init.sh
# still prints "successfully initialized". So we fetch the repositories from the current host ourselves and then
# verify that Defects4J works (the build fails here if not). EvoSuite/Gradle downloads also 404 but SoapFL does not use them.
RUN git clone https://github.com/rjust/defects4j.git /opt/defects4j \
 && git -C /opt/defects4j checkout v1.4.0 \
 && cd /opt/defects4j && ./init.sh || true
RUN cd /opt/defects4j/project_repos \
 && wget -q -O repos.zip https://defects4j.org/downloads/defects4j-repos.zip \
 && unzip -q repos.zip && mv defects4j/project_repos/* . && rm -rf defects4j repos.zip \
 && ls
RUN cd /opt/defects4j/framework/lib/build_systems/gradle \
 && wget -q https://defects4j.org/downloads/defects4j-gradle-dists-v3.zip https://defects4j.org/downloads/defects4j-gradle-deps-v3.zip \
 && mkdir -p dists && unzip -q -u defects4j-gradle-dists-v3.zip -d dists && unzip -q -u defects4j-gradle-deps-v3.zip \
 && rm -f defects4j-gradle-*-v3.zip && ls
RUN cd /opt/defects4j && cpanm --notest --installdeps .
RUN /opt/defects4j/framework/bin/defects4j info -p Lang > /tmp/d4j_info.txt && head -5 /tmp/d4j_info.txt
# the repositories must contain the exact commits of the 1.4.0 bug list: check out and compile one bug
RUN defects4j() { /opt/defects4j/framework/bin/defects4j "$@"; }; defects4j checkout -p Lang -v 1b -w /tmp/lang1 && defects4j compile -w /tmp/lang1 && rm -rf /tmp/lang1
ENV DEFECTS4J_HOME=/opt/defects4j PATH=/opt/defects4j/framework/bin:/opt/venv/bin:$PATH

# SoapFL at the pinned commit + our patch + its Defects4J overlay
ARG SOAPFL_COMMIT=c9f75f4f349849bc84d5cc50c4cc7dc70f012f16
RUN git clone https://github.com/IntHelloWorld/SoapFL.git /opt/SoapFL \
 && git -C /opt/SoapFL checkout ${SOAPFL_COMMIT}
COPY patches/ /tmp/patches/
RUN git -C /opt/SoapFL apply --whitespace=nowarn /tmp/patches/0001-open-model-support.patch \
 && cp -r /opt/SoapFL/Defects4J_mod/defects4j-1.4.0-jvm-mod/. /opt/defects4j/

COPY requirements.txt /tmp/requirements.txt
RUN python3.11 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt
# tiktoken vocabulary baked in so token counting works offline
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken
RUN mkdir -p $TIKTOKEN_CACHE_DIR && /opt/venv/bin/python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')" || true

ENV SOAPFL_DIR=/opt/SoapFL
WORKDIR /work
