# Stage 1: build the React app
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_API_URL=/api
ARG VITE_WS_URL=""
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL

RUN npm run build


# Stage 2: serve with nginx
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf.template

# Bake PORT substitution at runtime (PORT is always 8080 on Cloud Run)
# Bake API_URL into nginx config at build time
ARG API_URL
ARG PORT=8080

RUN sed -i "s|\$API_URL|${API_URL}|g" /etc/nginx/conf.d/default.conf.template && \
    sed -i "s|\$PORT|${PORT}|g" /etc/nginx/conf.d/default.conf.template && \
    mv /etc/nginx/conf.d/default.conf.template /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["/bin/sh", "-c", "envsubst '$PORT' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]