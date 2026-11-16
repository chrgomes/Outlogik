# Outlogik client portal and website admin (Angular, static files) served by nginx, with its
# own security headers. The API is routed to /api on the same address by App Platform.
FROM node:22-alpine AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npx ng build frontend \
 && node docker/app/csp.mjs dist/frontend/browser/index.html > /tmp/csp.conf

FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY docker/app/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/app/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY --from=build /tmp/csp.conf /etc/nginx/snippets/csp.conf
COPY --from=build /src/dist/frontend/browser /usr/share/nginx/html
EXPOSE 8080
