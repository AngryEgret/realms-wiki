FROM buildpack-deps:jessie

# Packages
RUN apt-get update &&\
    apt-get install -y \
      build-essential \
      python-pip \
      python-virtualenv \
      python-dev \
      zlib1g-dev \
      libffi-dev \
      libyaml-dev &&\
  # Add deploy user
    adduser --disabled-login --gecos '' deploy &&\
    adduser deploy sudo &&\
    echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers &&\
  # Virtualenv
    virtualenv /home/deploy/realms-wiki/.venv &&\
    cd /home/deploy/realms-wiki &&\
    .venv/bin/pip install realms-wiki &&\
  # Clear some fat
    apt-get clean &&\
    rm -rf \
      /var/lib/apt/lists/* \
      /tmp/* \
      /var/tmp/*

# Add start script
ADD realms-wiki.sh /home/deploy/run.sh
RUN chmod +x /home/deploy/run.sh

ENTRYPOINT ["/bin/su", "-m", "deploy", "-c", "/home/deploy/run.sh"]
CMD []

EXPOSE 5000
