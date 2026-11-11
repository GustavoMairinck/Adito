# Build stage
FROM node:22-slim AS build-stage

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the app and build
COPY . .
ARG VITE_API_URL=http://localhost:8001
ARG VITE_API_TIMEOUT=30000
ARG VITE_ACESSO_CIDADAO_AUTH_URL=http://localhost:8001/api/acesso-cidadao/authorize
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_API_TIMEOUT=$VITE_API_TIMEOUT
ENV VITE_ACESSO_CIDADAO_AUTH_URL=$VITE_ACESSO_CIDADAO_AUTH_URL
RUN npm run build

# Production stage
FROM nginx:stable-alpine AS production-stage

# Copy a custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the build output to nginx
COPY --from=build-stage /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
