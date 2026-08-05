# Multi-stage frontend build served by nginx for compose all-in-one demos.
FROM node:22-bookworm-slim AS build
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
# Vite inlines VITE_* vars at build time; runtime container env has no effect.
ARG VITE_ADAPTIVE_RAG_API_BASE_URL=""
ENV VITE_ADAPTIVE_RAG_API_BASE_URL=${VITE_ADAPTIVE_RAG_API_BASE_URL}
RUN pnpm build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
