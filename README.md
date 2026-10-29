# FinSight AI

FinSight AI helps you research company reports. Upload a PDF, ask a question, and inspect the passages behind the answer. Each citation links to a physical page in the original report.

The app extracts text and tables with Docling, searches report passages with Sentence Transformers and Qdrant, and generates answers with Gemini, OpenRouter, or a local Ollama model.

## What you can do

- Upload a report with its company and year, then track its processing status.
- Browse extracted passages and open their source pages.
- Ask questions about one selected report and inspect the retrieved evidence.
- Choose a free OpenRouter model, a Gemini model, or a local Ollama model.

## How it works

1. FastAPI saves the PDF and its metadata, then processes the report in the background. Docling extracts page-grounded text, headings, and tables. SQLite stores the report record and passages.
2. On the first question, Sentence Transformers generates embeddings for the report passages and Qdrant stores them. Changed passages are reindexed on the next question.
3. The question is embedded and matched against the selected report. The app restores nearby text or table context and sends the evidence to the chosen model.
4. The model returns an answer and citation IDs. The app checks those IDs and displays links to the original PDF pages.

PDFs and SQLite data live in `data/`. Docker volumes store Qdrant vectors and Ollama models across restarts.

## Requirements

- Python 3.10 or newer
- Node.js 20.19+ or 22.12+
- Docker and Docker Compose
- An OpenRouter or Gemini API key, or enough memory to run an Ollama model locally

Docling and the embedding model download assets on first use. Docling can require several gigabytes of memory and disk space, and long reports can take time to process on a CPU.

## Run locally

Start Qdrant from the project root:

```sh
docker compose up -d qdrant
```

In a terminal, create the Python environment and start the backend:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

The PyTorch command installs CPU builds. Choose a suitable PyTorch build for your machine if you need GPU support.

In another terminal, start the frontend:

```sh
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The API documentation is at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Enter a company and year, upload a PDF, and wait for its status to become **Ready**. Select the report in **Ask a question**, choose a provider, and submit a question. Open a report in the library to inspect its passages or retry processing.

## Choose an answer provider

### OpenRouter

Create an [OpenRouter API key](https://openrouter.ai/settings/keys), select **OpenRouter · Free**, and enter the key. **Auto · Free models** uses `openrouter/free`; the selector also lists free models that advertise JSON response support. Refresh the list to load the current catalog.

The backend accepts only `openrouter/free` and model IDs ending in `:free`. Free models can have usage limits and variable availability. See the [OpenRouter free router documentation](https://openrouter.ai/docs/guides/routing/routers/free-router).

### Gemini

Create a [Gemini API key](https://aistudio.google.com/apikey), select **Gemini · Google**, and enter the key. Choose Gemini 3.5 Flash-Lite or Gemini 3.8 Flash. Usage depends on your Google project's quota and billing settings. See [Google's model documentation](https://ai.google.dev/gemini-api/docs/models).

### Ollama

Start Ollama and pull the default model:

```sh
docker compose up -d ollama
docker compose exec ollama ollama pull bonsai-2:2b
```

Select **Ollama · Local**. No API key is required.

For the NVIDIA GPU override on Linux, start the services with:

```sh
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

The override expects NVIDIA device nodes and driver libraries under `/usr/lib/x86_64-linux-gnu`. Use the standard Compose configuration on other systems.

## Configuration

Set environment variables before starting the backend. The defaults are listed in [.env.example](.env.example).

| Variable | Default | Purpose |
| --- | --- | --- |
| `QDRANT_URL` | `http://127.0.0.1:6333` | Qdrant endpoint |
| `FINSIGHT_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Passage and question embedding model |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `bonsai-2:2b` | Local answer model |
| `OPENROUTER_API_KEY` | Empty | Optional backend OpenRouter key |
| `GEMINI_API_KEY` | Empty | Optional backend Gemini key |
| `FINSIGHT_DATA_DIR` | `data/` in the project root | PDF and SQLite storage directory |

To keep a provider key on the backend, copy `.env.example` to `.env`, add the key, and start the backend with:

```sh
uvicorn app.main:app --app-dir backend --reload --env-file .env
```

The regular startup command does not load `.env` automatically. `.env` files are ignored by Git. A key entered in the app remains in memory until you reload the page or switch providers; it is not stored in the database or browser storage.

OpenRouter and Gemini receive the question and retrieved passages. With the default local endpoints, extraction, embeddings, Qdrant, and Ollama run locally. Changing service URLs can send report content to another host.

## API

| Endpoint | Purpose |
| --- | --- |
| `POST /documents` | Upload a PDF and start processing |
| `GET /documents` | List reports and their status |
| `POST /documents/{id}/process` | Retry or repeat processing |
| `GET /documents/{id}/chunks` | Inspect extracted passages |
| `GET /documents/{id}/file` | Open the original PDF |
| `POST /questions` | Ask a question about one report |
| `GET /models/openrouter` | List compatible free OpenRouter models |
| `GET /models/gemini` | List the built-in Gemini choices |

A question request can choose a provider:

```json
{
  "question": "What was revenue in 2022?",
  "document_id": "your-document-id",
  "generation": {
    "provider": "gemini",
    "model": "gemini-3.5-flash-lite"
  }
}
```

Set `GEMINI_API_KEY` on the backend or include `api_key` in the `generation` object. For OpenRouter, use `"provider": "openrouter"` and a free model such as `"openrouter/free"`. Requests that omit `generation` use Ollama. The response contains the answer, citations, retrieved passages, and model name.

## Tests

With the backend environment activated, run:

```sh
PYTHONPATH=backend python -m unittest discover -s backend/tests -v
```

Build the frontend with:

```sh
cd frontend
npm run build
```

## Limitations

- Answers can misread figures or cite passages that do not support a claim. Check the linked PDF before relying on an answer.
- Table extraction can lose or misinterpret headers. Items that span multiple PDF pages are omitted because they cannot be assigned to one page reliably.
- Retrieval uses dense search. Hybrid search, reranking, controlled calculations, and benchmark evaluation are described in [plan.md](plan.md) but are not implemented.
- Questions currently target one report. The background processor is intended for a single local server process.
- A model response without citations produces an error. An explicit insufficient-evidence response produces an "I don't know" answer.
