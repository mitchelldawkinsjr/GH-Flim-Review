# Minimal PocketBase image from the official prebuilt binary.
# (PocketBase publishes no Docker image; this is the docs-recommended pattern.)
FROM alpine:latest

ARG PB_VERSION=0.40.4
ARG TARGETARCH=amd64

RUN apk add --no-cache unzip ca-certificates

ADD https://github.com/pocketbase/pocketbase/releases/download/v${PB_VERSION}/pocketbase_${PB_VERSION}_linux_${TARGETARCH}.zip /tmp/pb.zip
RUN unzip /tmp/pb.zip -d /pb/ && rm /tmp/pb.zip

VOLUME /pb_data
EXPOSE 8090

CMD ["/pb/pocketbase", "serve", "--http=0.0.0.0:8090", "--dir=/pb_data", "--publicDir=/pb_public"]
