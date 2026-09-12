FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
ARG VITE_API_URL
ARG VITE_TURNSTILE_SITE_KEY
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_TURNSTILE_SITE_KEY=${VITE_TURNSTILE_SITE_KEY}
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=frontend-build /app/dist /usr/share/nginx/html
EXPOSE 80
