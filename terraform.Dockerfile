# Build stage
FROM python:3.12-slim AS builder

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y gnupg wget lsb-release && \
    wget -O- https://apt.releases.hashicorp.com/gpg | \
    gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
    tee /etc/apt/sources.list.d/hashicorp.list > /dev/null && \
    wget -O- https://download.docker.com/linux/debian/gpg | \
    gpg --dearmor -o /usr/share/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y terraform=1.12.* docker-ce-cli && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Final stage
FROM python:3.12-slim

COPY --from=builder /usr/bin/terraform /usr/bin/terraform
COPY --from=builder /usr/share/keyrings/hashicorp-archive-keyring.gpg /usr/share/keyrings/
COPY --from=builder /usr/bin/docker /usr/bin/docker
COPY --from=builder /usr/share/keyrings/docker.gpg /usr/share/keyrings/

RUN apt-get update && apt-get install -y build-essential git && \
    pip install --no-cache-dir awscli

ENTRYPOINT ["/usr/bin/terraform"]
