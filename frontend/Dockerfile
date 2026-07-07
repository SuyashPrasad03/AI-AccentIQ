FROM node:20-slim

WORKDIR /app

# Install dependencies (layer-cached separately from source)
COPY package.json ./
RUN npm install

# Copy source (dev volume mount will override this in docker-compose)
COPY . .

EXPOSE 5173

# Vite dev server with HMR
CMD ["npm", "run", "dev"]
