# Builds chickenzord/linkding-mcp from source for the target architecture.
#
# Why we don't use ghcr.io/chickenzord/linkding-mcp directly: its Dockerfile
# hardcodes `GOARCH=amd64`, so the published arm64 image ships an x86-64 binary
# and dies with "exec format error" on ARM64 (the Pi deploy target). We build
# for the native arch instead. See docs/mcp/CONVENTIONS.md and issue #15.
FROM golang:1.25-alpine AS builder

# Pin the upstream source tag (git releases use the `v` prefix).
ARG VERSION=v0.1.6
# Set automatically by BuildKit (arm64 on the Pi, amd64 on x86 dev hosts).
ARG TARGETARCH

RUN apk add --no-cache git
WORKDIR /build
RUN git clone --depth 1 --branch "${VERSION}" \
    https://github.com/chickenzord/linkding-mcp.git .
RUN go mod download
RUN CGO_ENABLED=0 GOOS=linux GOARCH=${TARGETARCH} go build \
    -ldflags="-w -s -X 'github.com/chickenzord/linkding-mcp/internal/version.Version=${VERSION}'" \
    -o linkding-mcp ./cmd/linkding-mcp

# Runtime stage — mirrors the upstream runtime image (alpine + ca-certificates,
# non-root UID/GID 1000).
FROM alpine:latest
RUN apk --no-cache add ca-certificates tzdata && \
    addgroup -g 1000 -S appgroup && \
    adduser -u 1000 -S appuser -G appgroup
WORKDIR /app
COPY --from=builder /build/linkding-mcp .
USER appuser
ENTRYPOINT ["/app/linkding-mcp"]
