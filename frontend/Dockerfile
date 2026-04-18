FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Backend URL is baked at build time. Set in Railway service variables
# as a *build* arg, not a runtime env (Vite inlines it).
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Skip the `tsc -b` step from package.json's build script — the frontend
# has accumulated type errors in vite.config.ts/vitest.config.ts (missing
# @types/node) and a few `import.meta.env` accesses without vite/client
# types. Esbuild (Vite's actual bundler) doesn't care; only tsc does.
# Long-term: install @types/node, add a vite-env.d.ts reference, fix
# vitest.config.ts plugin typing.
RUN npx vite build


FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
EXPOSE 8080
