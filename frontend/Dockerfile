FROM node:20-alpine
WORKDIR /app
COPY . /app
ENV HOST=0.0.0.0
ENV PORT=5173
RUN if [ -f package.json ]; then npm install; fi
EXPOSE 5173
CMD ["sh", "-c", "if [ -f package.json ]; then npm run dev -- --host 0.0.0.0 --port 5173; else echo 'Frontend package.json not implemented yet. Phase 0.1 will create Vite app.' && sleep infinity; fi"]
