# TOI Style Guide RAG

Production-oriented RAG chat application for the Times of India style guide PDFs. The stack is:

- Frontend: React + Vite
- Backend: FastAPI
- Database: Supabase Postgres + pgvector
- LLM/embeddings: OpenAI

## Folder structure

```text
.
├── backend
│   ├── app
│   │   ├── api
│   │   ├── core
│   │   ├── schemas
│   │   └── services
│   ├── scripts
│   ├── .env.example
│   └── requirements.txt
├── frontend
│   ├── src
│   │   ├── components
│   │   ├── lib
│   │   └── styles
│   ├── .env.example
│   └── package.json
├── sql
│   └── init.sql
├── new_media_words_glossary.pdf
├── TOI STYLE GUIDE, March2010, EDITION I.pdf
└── README.md
```

## Features

- PDF text extraction with `pypdf`
- Sentence-aware chunking with overlap
- OpenAI embeddings stored in Supabase `pgvector`
- Cosine similarity retrieval with source citations
- FastAPI `/chat` and `/ingest` endpoints
- FastAPI `/status` endpoint for readiness checks
- Responsive React chat UI with citations and loading states
- One-click PDF ingestion from the frontend
- Duplicate-safe ingestion using `chunk_hash`

## 1. Database setup

Run the SQL in [sql/init.sql](/Users/deepaliyadav/Desktop/codebase/TIMES_CODEBASE/TOI-style-guide-RAG/sql/init.sql) inside the Supabase SQL editor.

Notes:

- The schema uses `vector(1536)` for `text-embedding-3-small`.
- If you switch to a different embedding model dimension, update the SQL schema and `EMBEDDING_DIMENSION`.
- After large ingests, run `analyze document_chunks;` in Supabase so the IVFFlat index stays effective.

## 2. Backend setup

```bash
cd /Users/deepaliyadav/Desktop/codebase/TIMES_CODEBASE/TOI-style-guide-RAG/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set these values in `backend/.env`:

```env
OPENAI_API_KEY=...
DATABASE_URL=postgresql://postgres:<password>@db.<project>.supabase.co:5432/postgres
OPENAI_CHAT_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_TRUST_ENV=false
OPENAI_VERIFY_SSL=true
EMBEDDING_BATCH_SIZE=64
DOCUMENTS_DIR=..
```

Start the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 3. Ingest the PDFs

With the backend environment active, either:

```bash
python -m scripts.ingest
```

or call the HTTP endpoint:

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"reset_existing": true}'
```

If you want to ingest explicit files:

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"file_paths": ["../new_media_words_glossary.pdf", "../TOI STYLE GUIDE, March2010, EDITION I.pdf"]}'
```

## 4. Frontend setup

```bash
cd /Users/deepaliyadav/Desktop/codebase/TIMES_CODEBASE/TOI-style-guide-RAG/frontend
npm install
cp .env.example .env
npm run dev
```

The frontend expects the API at `http://localhost:8000` by default.

Once the UI loads, click `Ingest PDFs` in the left panel to index the bundled PDFs without running the script manually.

If your office network performs TLS interception and OpenAI calls fail with `CERTIFICATE_VERIFY_FAILED`, either:

- set `OPENAI_CA_BUNDLE=/absolute/path/to/your/company-root-ca.pem`, or
- as a temporary local-only fallback, set `OPENAI_VERIFY_SSL=false`

The CA bundle option is the safer production choice.

## 5. API contract

### `POST /chat`

Request:

```json
{
  "query": "How should numerals be used in headlines?",
  "history": [
    { "role": "user", "content": "Previous question" },
    { "role": "assistant", "content": "Previous answer" }
  ],
  "top_k": 6
}
```

Response:

```json
{
  "answer": "Grounded answer here",
  "sources": [
    {
      "id": "uuid",
      "document_name": "TOI STYLE GUIDE, March2010, EDITION I.pdf",
      "page_number": 12,
      "chunk_index": 1,
      "content": "Relevant excerpt",
      "similarity": 0.88
    }
  ],
  "retrieved_at": "2026-04-08T00:00:00Z"
}
```

### `POST /ingest`

Request:

```json
{
  "file_paths": ["../new_media_words_glossary.pdf"],
  "reset_existing": false
}
```

## 6. Production notes

- Keep secrets in environment variables only.
- Add Supabase connection pooling if you expect higher concurrency.
- For larger corpora, batch inserts and embeddings more aggressively.
- You can add a `/chat/stream` SSE endpoint later without changing the retrieval layer.
- For stricter grounding, tune the prompt and add answer refusal when top similarity is below a threshold.

## 7. Deployment

### Vercel

Best use in this repo:

- Deploy the FastAPI backend as one Vercel project with `backend` as the project root.
- Optionally deploy the React frontend as a second Vercel project with `frontend` as the root.

Backend notes:

- Vercel supports Python applications and FastAPI on its Python runtime. Official docs: [Vercel Python](https://vercel.com/docs/functions/runtimes/python), [Vercel Frameworks](https://vercel.com/docs/frameworks/backend/fastapi).
- This repo now includes [index.py](/Users/deepaliyadav/Desktop/codebase/TIMES_CODEBASE/TOI-style-guide-RAG/backend/index.py), so if `backend` is the Vercel root, Vercel can import the FastAPI app directly.

Backend environment variables to set in Vercel:

```env
OPENAI_API_KEY=...
OPENAI_CHAT_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
DATABASE_URL=postgresql://...
OPENAI_TRUST_ENV=false
OPENAI_VERIFY_SSL=true
EMBEDDING_BATCH_SIZE=64
DOCUMENTS_DIR=..
CORS_ORIGINS=https://your-frontend-domain.vercel.app,https://your-frontend-domain.netlify.app
```

Frontend environment variable in Vercel:

```env
VITE_API_BASE_URL=https://your-backend-project.vercel.app
```

Important:

- The backend reads the PDFs from the repository, so keep the PDF files committed in the deployment.
- Serverless streaming can work on Vercel, but test `/chat/stream` after deploy. If your plan/runtime limits interfere, fall back temporarily to `/chat`.

### Netlify

Recommended use in this repo:

- Deploy the React frontend on Netlify.
- Keep the FastAPI backend on Vercel or another Python-friendly host.

Why:

- Netlify’s core Functions platform is primarily oriented around JavaScript/TypeScript and Go workflows from their current platform docs: [Netlify Functions](https://www.netlify.com/platform/core/functions).
- For this exact FastAPI backend, Vercel is the simpler host.

This repo now includes [netlify.toml](/Users/deepaliyadav/Desktop/codebase/TIMES_CODEBASE/TOI-style-guide-RAG/netlify.toml) for the frontend build.

Netlify frontend settings:

- Base directory: `frontend`
- Build command: `npm run build`
- Publish directory: `dist`

Frontend environment variable in Netlify:

```env
VITE_API_BASE_URL=https://your-backend-project.vercel.app
```

### Recommended architecture

For the least friction:

1. Deploy `backend` to Vercel.
2. Deploy `frontend` to Netlify.
3. Set `VITE_API_BASE_URL` in Netlify to the Vercel backend URL.
4. Set `CORS_ORIGINS` in Vercel to allow the Netlify frontend domain.

### Deploy checklist

1. Run the Supabase SQL from [init.sql](/Users/deepaliyadav/Desktop/codebase/TIMES_CODEBASE/TOI-style-guide-RAG/sql/init.sql).
2. Confirm the PDFs are committed in the repo.
3. Deploy backend from `backend` root on Vercel.
4. Deploy frontend from `frontend` root on Netlify or Vercel.
5. Set `VITE_API_BASE_URL` to the backend URL.
6. Set `CORS_ORIGINS` to the deployed frontend domain.
7. After deploy, call `/status`, then run `/ingest`, then test `/chat` and `/chat/stream`.
