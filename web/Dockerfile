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
RUN node render-nginx.cjs

FROM nginx:1.30-alpine AS runtime-files
# Copy only nginx and its shared libraries into an empty runtime; no BusyBox,
# shell, apk, envsubst or nginx shell startup scripts survive this stage.
RUN mkdir -p /rootfs/usr/sbin /rootfs/etc/nginx /rootfs/tmp \
    && chmod 1777 /rootfs/tmp \
    && cp /usr/sbin/nginx /rootfs/usr/sbin/ \
    && cp /etc/nginx/mime.types /rootfs/etc/nginx/ \
    && for lib in $(ldd /usr/sbin/nginx | awk '$1 ~ /^\// {print $1} $3 ~ /^\// {print $3}'); do cp -L --parents "$lib" /rootfs; done
COPY nginx.conf /rootfs/etc/nginx/nginx.conf
COPY --from=build /app/nginx.rendered.conf /rootfs/etc/nginx/conf.d/default.conf

FROM scratch
COPY --from=runtime-files /rootfs /
COPY --from=build /app/dist /usr/share/nginx/html
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["/usr/sbin/nginx", "-e", "/dev/stderr"]
CMD ["-g", "daemon off;"]
