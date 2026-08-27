# magicpin Vera AI — Standalone Backend Deployment

This directory contains the production-ready backend service for **magicpin Vera AI Challenge**.

---

## 🚀 Quick Deployment Guide (Railway / Render / Docker)

### Option 1: Deploy on Railway (Recommended)
1. **Push your repository** to GitHub.
2. Go to [Railway.app](https://railway.app) and create a **New Project** $\rightarrow$ **Deploy from GitHub repo**.
3. Railway automatically detects `railway.toml` and `Dockerfile`.
4. In the **Variables** tab, add your secrets:
   - `GROQ_API_KEY` = `your_groq_api_key`
   - `LLM_PROVIDER` = `groq`
   - `DB_PATH` = `/data/magicpin_vera.db`
5. In **Settings** $\rightarrow$ **Volumes**, add a persistent volume mounted at `/data`.
6. Once deployed, verify your public healthz endpoint:
   ```bash
   curl https://<YOUR-RAILWAY-DOMAIN>/v1/healthz
   ```

---

### Option 2: Deploy on Render
1. Go to [Render.com](https://render.com) and create a **New Web Service**.
2. Connect your GitHub repository.
3. Select **Docker** environment.
4. Set instance type to **Starter** (Always-on recommended for judge evaluation to eliminate cold starts).
5. In **Advanced** $\rightarrow$ **Disks**, add a persistent disk mounted at `/data` (1GB).
6. Set environment variable `GROQ_API_KEY` in Render dashboard.
7. Verify public endpoint:
   ```bash
   curl https://<YOUR-RENDER-DOMAIN>/v1/healthz
   ```

---

### Option 3: Run with Docker Locally
```bash
# Build the Docker image
docker build -t magicpin-vera:latest .

# Run with persistent volume mount and Groq key
docker run -d \
  --name magicpin-vera \
  -p 8080:8080 \
  -v $(pwd)/vera_data:/data \
  -e PORT=8080 \
  -e DB_PATH=/data/magicpin_vera.db \
  -e LLM_PROVIDER=groq \
  -e GROQ_API_KEY="your_groq_api_key_here" \
  magicpin-vera:latest
```

---

## 📡 Public API Endpoints

- `GET  /v1/healthz` — Liveness & loaded context counts probe
- `GET  /v1/metadata` — Team, model, and submission metadata
- `POST /v1/context` — Atomic context ingestion & versioning
- `POST /v1/tick` — Periodic wake-up for proactive outreach
- `POST /v1/reply` — Multi-turn conversation interaction
