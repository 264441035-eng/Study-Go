# --- build stage ---
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
# AI Tutor の URL。既定は空 = 同一 ALB オリジンへ相対アクセス (/sessions* を相乗り)。
# ローカルの `npm run build` (未指定) は aiTutor.ts 側で localhost:8000 に落ちる。
ARG VITE_AI_TUTOR_URL=""
ENV VITE_AI_TUTOR_URL=$VITE_AI_TUTOR_URL
RUN npm run build

# --- runtime stage ---
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
