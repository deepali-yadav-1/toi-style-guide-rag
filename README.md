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
# toi-style-guide-rag
