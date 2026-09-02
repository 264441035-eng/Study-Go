# --- build stage ---
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
# backend API のベース URL。既定は空 = 同一 ALB オリジンへ相対アクセス (/api/* を相乗り)。
# 空文字は auth.ts の `?? "http://localhost:8000"` に対して nullish ではないので勝ち、
# ログイン fetch が `/api/auth/login`（相対）になる。未指定のローカル build は localhost:8000。
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
# AI Tutor の URL。既定は空 = 同一 ALB オリジンへ相対アクセス (/sessions* を相乗り)。
# ローカルの `npm run build` (未指定) は aiTutor.ts 側で localhost:8000 に落ちる。
ARG VITE_AI_TUTOR_URL=""
ENV VITE_AI_TUTOR_URL=$VITE_AI_TUTOR_URL
# Google Maps表示に使うAPIキー。ビルド時に埋め込まれる（秘密鍵ではなく、
# Google Cloud側でHTTPリファラー制限をかけた上で公開される前提のキー）。
ARG VITE_GOOGLE_MAPS_API_KEY=""
ENV VITE_GOOGLE_MAPS_API_KEY=$VITE_GOOGLE_MAPS_API_KEY
RUN npm run build

# --- runtime stage ---
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
