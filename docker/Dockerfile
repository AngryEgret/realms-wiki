FROM buildpack-deps:jessie

# Packages
RUN apt-get update && \
    apt-get install -y \
      build-essential \
      python-pip \
      python-virtualenv \
      python-dev \
      zlib1g-dev \
      libffi-dev \
      libyaml-dev

ADD user-setup.sh /tmp/user-setup.sh
RUN chmod +x /tmp/user-setup.sh ;\
    sync ;\
    /tmp/user-setup.sh

# Virtualenv
RUN virtualenv /home/deploy/realms-wiki/.venv && \
    cd /home/deploy/realms-wiki && \
    .venv/bin/pip install realms-wiki

ADD realms-wiki.sh /home/deploy/run.sh
RUN chmod +x /home/deploy/run.sh

# Clear some fat
RUN apt-get clean && \
  rm -rf \
    /var/lib/apt/lists/* \
    /tmp/* \
    /var/tmp/*

ENTRYPOINT ["/bin/su", "-m", "deploy", "-c", "/home/deploy/run.sh"]
CMD []

EXPOSE 5000
