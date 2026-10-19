FROM node:24-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
# Exact versions from the lockfile (reproducible builds).
RUN npm ci
COPY . .
# API URL baked into the bundle at build time.
ARG VUE_APP_API_URL=http://localhost:8001
ENV VUE_APP_API_URL=$VUE_APP_API_URL
RUN npm run build

FROM nginx:1.30-alpine
# Origin allowed in the Content-Security-Policy; override per deployment.
ENV API_ORIGIN=http://localhost:8001
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
