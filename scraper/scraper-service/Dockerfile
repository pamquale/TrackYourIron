FROM rust:latest AS builder
WORKDIR /usr/src/app
COPY Cargo.toml Cargo.lock ./
COPY src ./src
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y libssl-dev ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /usr/src/app/target/release/scraper-service /app/scraper-service
RUN chmod +x /app/scraper-service || true
CMD ["/app/scraper-service"]
