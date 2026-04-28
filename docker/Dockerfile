FROM node:20-bookworm-slim AS deps

WORKDIR /app

COPY web/package.json web/package-lock.json ./
RUN npm ci

FROM node:20-bookworm-slim AS builder

WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY web/ ./

RUN npm run build

FROM node:20-bookworm-slim AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=8230

COPY --from=builder --chown=node:node /app ./

USER node

EXPOSE 8230

CMD ["npx", "next", "start", "-H", "0.0.0.0", "-p", "8230"]
