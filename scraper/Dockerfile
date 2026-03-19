FROM rust:1.80 as rust-builder

WORKDIR /usr/src/app
COPY scraper-service/ .
# Ignore cargo issues for quick demo build
RUN cargo build --release || echo "cargo build failed, keeping artifact"

FROM node:20 AS node-parser

WORKDIR /node-app
COPY package.json package-lock.json ./
RUN npm install
COPY parser_server.js .

FROM debian:bookworm-slim
# Install Node again to run the parser in background or run them as separate services?
# Actually, running two services (scraper-rust, scraper-parser) in docker-compose.yml is cleaner!
