FROM ghcr.io/foundry-rs/foundry:latest

WORKDIR /sandbox
COPY entrypoint.sh /sandbox/entrypoint.sh
RUN chmod +x /sandbox/entrypoint.sh

EXPOSE 8545
ENTRYPOINT ["/sandbox/entrypoint.sh"]