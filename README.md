# FinSight AI

FinSight AI is a financial research assistant under development. The report library accepts PDFs and extracts page-grounded passages using Docling. See [plan.md](plan.md) for the full project plan.

## Run locally

Requirements: Python 3.10+ and Node.js 20.19+ or 22.12+.

In one terminal (the PyTorch command installs CPU builds; choose the appropriate PyTorch installation for your system if needed):

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

In another terminal:

```sh
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, enter a company and report year, and upload a PDF. New uploads are processed automatically. To process a report uploaded before phase 2, select it and choose **Process report**. Select a report to inspect its passages and open the source PDF at the physical page number. Reports, passages, and SQLite metadata are stored in `data/` and persist across restarts.

Docling downloads model assets on first use and can require several gigabytes of disk space and memory; processing a long report on CPU can take time. Extracted tables and page links should be checked against the original PDF before relying on them. Items spanning multiple PDF pages are omitted because they cannot be assigned to one page reliably. Interrupted or failed processing can be retried from the report view. The background processor is intended for a single local server process. The API is available at http://127.0.0.1:8000/docs.

## Ask questions (phase 3)

Start Qdrant for report search:

```sh
docker compose up -d qdrant
```

In the app, select a ready report, choose an answer provider, enter a question, and select **Ask question**. The first question builds the report's dense vector index; the embedding model downloads on first use. A changed report is reindexed when next queried. The answer includes model-selected citations and retrieved passages with links to physical PDF pages.

Search ranks small segments, then restores their source context before generation. Table matches include the source table, or matching rows and nearby rows for large tables, with nearby units from the same page. Text matches include adjacent passages from the same page and section. Overview questions also receive the report cover. The prompt includes report metadata and section names. An answer missing citations produces a citation error; only an explicit insufficient-evidence answer uses the "I don't know" fallback.

### Use OpenRouter free models

1. Create an [OpenRouter API key](https://openrouter.ai/settings/keys).
2. Select **OpenRouter · Free** and paste the key into **API key**.
3. Use **Auto · Free models**, or select a specific free model. Use the refresh button to reload the current choices.

The app defaults to `openrouter/free`. OpenRouter selects an available free model that supports the requested response format. The model list comes from OpenRouter's current catalog and includes `:free` models advertising JSON response support. The backend rejects paid model IDs. There is no automatic switch to paid models or Ollama after an OpenRouter failure. Free models have account limits and variable availability and latency. See [OpenRouter's free-router documentation](https://openrouter.ai/docs/guides/routing/routers/free-router).

The backend sends the question and retrieved passages to OpenRouter and its model provider. PDF extraction, embeddings, and Qdrant search still run locally. The app keeps a pasted key in memory until you reload or switch providers. It does not save the key to browser storage or the database. Answers show the model OpenRouter actually used.

To keep the key on the backend instead, copy `.env.example` to `.env`, set `OPENROUTER_API_KEY`, and restart the backend with:

```sh
uvicorn app.main:app --app-dir backend --reload --env-file .env
```

The key field then shows **Using server key** and can remain empty. `.env` files are ignored by Git. The regular startup command does not load `.env` automatically.

### Use the Gemini API

1. Create a [Gemini API key in Google AI Studio](https://aistudio.google.com/apikey).
2. Select **Gemini · Google** and paste the key into **API key**.
3. Choose **Gemini 3.5 Flash-Lite** or **Gemini 3.8 Flash** and ask a question.

The built-in choices come from [Google's model documentation](https://ai.google.dev/gemini-api/docs/models). Gemini uses Google's API directly. Google receives the question and retrieved passages; PDF processing and retrieval remain local. Keys entered in the app stay in memory and are cleared when you reload or switch providers. Gemini usage follows your Google project's quota and billing settings.

To use a backend key, set `GEMINI_API_KEY` in `.env` and start the backend with `--env-file .env`, as shown above. The key field can then remain empty. API clients can add `"generation": {"provider": "gemini", "model": "gemini-3.5-flash-lite"}` to `POST /questions`, with an optional per-request `api_key`. Responses retain the same citations and PDF links. The integration uses [Gemini structured JSON output](https://ai.google.dev/gemini-api/docs/generate-content/structured-output) and rejects blocked, incomplete, or invalid answers.

### Use a local model with Ollama

Start Ollama and download the answer model:

```sh
docker compose up -d ollama
docker compose exec ollama ollama pull bonsai-2:2b
```

Select **Ollama · Local** in the app. No API key is needed. Existing API clients that omit the `generation` field continue to use Ollama. To request OpenRouter through `POST /questions`, add `"generation": {"provider": "openrouter", "model": "openrouter/free"}`. Supply a per-request `api_key` inside that object or configure `OPENROUTER_API_KEY` on the backend.

Configuration: `QDRANT_URL` defaults to `http://127.0.0.1:6333`, `OLLAMA_URL` to `http://127.0.0.1:11434`, `OLLAMA_MODEL` to `bonsai-2:2b`, and `FINSIGHT_EMBEDDING_MODEL` to `sentence-transformers/all-MiniLM-L6-v2`. Set these environment variables before starting the backend to use other local services or models. Compose volumes persist model and vector data. Run `docker compose stop` to stop the services.

This is a dense-retrieval baseline: the model can misread figures or cite an irrelevant passage, and complex table headers can be extracted incorrectly. Check answers against the linked PDF. Calculations, hybrid retrieval, reranking, and evaluation are later phases. The Ollama defaults process report data locally after model downloads; changing service URLs can send report content elsewhere.

### NVIDIA GPU on this Linux machine

To expose the NVIDIA GPU to Ollama without the NVIDIA Container Toolkit, start with the GPU override:

```sh
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

The override uses the host NVIDIA device nodes and driver libraries at `/usr/lib/x86_64-linux-gnu`. It is specific to Linux systems with those paths; use the standard Compose command on other systems. Stop a loaded model with `docker compose exec ollama ollama stop bonsai-2:2b`.
