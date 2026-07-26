# DocuMind — Deployment Guide

This guide deploys DocuMind for free:
- **Backend** → [Render](https://render.com) free tier
- **Frontend** → [Vercel](https://vercel.com) free tier

Total cost: **$0** (Groq LLM is free, sentence-transformers embeddings are local)

> **Note on Render free tier**: Free web services spin down after 15 minutes of inactivity. The first request after sleeping takes ~30s to wake up. Upgrade to Render's $7/month Starter plan to avoid this.

---

## Prerequisites

1. Push your code to GitHub (see [GitHub Setup](#github-setup) below)
2. Get a free [Groq API key](https://console.groq.com)

---

## GitHub Setup

```bash
# From the documind/ root
git init
git add .
git commit -m "feat: initial DocuMind implementation"

# Create a new repo on github.com, then:
git remote add origin https://github.com/<your-username>/documind.git
git branch -M main
git push -u origin main
```

---

## Backend — Render

### 1. Create account
Go to [render.com](https://render.com) → Sign up (free, no credit card)

### 2. New Web Service
- **New** → **Web Service**
- Connect your GitHub repo
- Select the `documind` repository

### 3. Configure build settings

| Setting | Value |
|---|---|
| **Root Directory** | `backend` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | Free |

### 4. Environment Variables

In the Render dashboard → **Environment**, add:

```
LLM_PROVIDER          = groq
GROQ_API_KEY          = gsk_your_key_here
EMBEDDING_PROVIDER    = local
CHROMA_PERSIST_DIR    = ./data/chroma_db
FRONTEND_URL          = https://your-app.vercel.app
```

> ⚠️ **Important**: ChromaDB data on Render's free tier is **ephemeral** — it resets on each deploy. This means uploaded documents are lost when the service restarts. For persistence, either upgrade to a paid Render plan (which includes a persistent disk) or use a cloud vector store like Pinecone.

### 5. Deploy
Click **Create Web Service**. Render will build and deploy your backend.
Note your backend URL: `https://documind-backend.onrender.com`

---

## Frontend — Vercel

### 1. Create account
Go to [vercel.com](https://vercel.com) → Sign up with GitHub (free)

### 2. Import project
- **Add New** → **Project**
- Import your `documind` GitHub repository

### 3. Configure build settings

| Setting | Value |
|---|---|
| **Root Directory** | `frontend` |
| **Framework Preset** | Vite |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |

### 4. Point frontend at your backend

Before deploying, update the API base URL in the frontend:

In `frontend/src/components/FileUpload.jsx` and `ChatInterface.jsx`, replace:
```js
fetch('http://localhost:8000/api/...')
```
with:
```js
fetch('https://documind-backend.onrender.com/api/...')
```

Or better — use an environment variable:

**Create `frontend/.env.production`:**
```
VITE_API_URL=https://documind-backend.onrender.com
```

**In your components:**
```js
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
fetch(`${API}/api/upload`, ...)
```

### 5. Deploy
Click **Deploy**. Vercel will build and give you a URL like `https://documind.vercel.app`.

### 6. Update backend CORS
In Render, update the `FRONTEND_URL` env var to your Vercel URL:
```
FRONTEND_URL = https://documind.vercel.app
```

---

## Verify deployment

```bash
# Health check
curl https://documind-backend.onrender.com/health
# → {"status":"ok"}

# Swagger UI
open https://documind-backend.onrender.com/docs
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Backend crashes on startup | Check Render logs. Usually a missing env var or `pip install` failure |
| CORS errors in browser | Ensure `FRONTEND_URL` in Render matches your exact Vercel URL |
| "Model not found" | First request downloads the embedding model (~90 MB). Render free tier may time out. Use `EMBEDDING_PROVIDER=openai` for cloud deploys |
| ChromaDB data lost on redeploy | Expected on free tier. Add Render persistent disk ($1/month for 1 GB) |
| Groq rate limit | Free tier: 30 req/min. Add retry logic or upgrade Groq plan |
