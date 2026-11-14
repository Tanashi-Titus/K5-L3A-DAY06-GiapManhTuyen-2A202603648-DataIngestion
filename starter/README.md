# Data ingestion pipeline and chat demo

The project uses a text-based PDF corpus, Chroma persistent storage, local EmbeddingGemma 2 embeddings, and a Flask chat demo backed by Mistral. It runs with the Miniconda base Python at `D:\miniconda3\python.exe`; do not create another environment.

## Setup

From this directory, install the project dependencies into the existing Miniconda base if they are not already installed:

```powershell
D:\miniconda3\python.exe -m pip install -r requirements-app.txt
Copy-Item .env.example .env
```

Set `MISTRAL_API_KEY` in `.env`. Keep `.env` local; Git ignores it. The default chat model is `ministral-8b-latest`. Set `EMBEDDING_MODEL` only if the local EmbeddingGemma 2 model is not at the path configured in `src/embeddings.py`.

## Ingest the corpus

Run from `starter/`:

```powershell
D:\miniconda3\python.exe -m src.run ingest `
  --pdf ../data/data.pdf `
  --pdf ../data/quantum-oscillator.pdf `
  --document-id arxiv-1204.0653-v1 `
  --document-id mdpi-entropy-2023-25-213 `
  --source data/data.pdf `
  --source data/quantum-oscillator.pdf `
  --metadata ../data/data_pdf_page_metadata.json `
  --metadata ../data/quantum_oscillator_page_metadata.json
```

The main PDF is not included in Git because its redistribution terms have not been verified. Download arXiv v1 using the URL in `data/corpus_manifest.json` and confirm its SHA-256 there. The supplemental PDF is CC BY 4.0; keep its attribution and source. Both PDFs have a text layer, so this corpus does not require OCR.

Ingestion creates persistent Chroma collections under `results/chroma/` and JSON statistics in `results/`. The database and local embedding model are generated/downloaded locally, not committed.

## Run benchmark and audit

```powershell
D:\miniconda3\python.exe -m src.run benchmark --benchmark ../benchmark/questions.json --split dev
D:\miniconda3\python.exe -m src.run select --strategy C --rationale "Dev: Hit@3 tied; C has the highest Hit@1"
D:\miniconda3\python.exe -m src.run benchmark --benchmark ../benchmark/questions.json --split test
D:\miniconda3\python.exe -m src.audit
D:\miniconda3\python.exe -m unittest discover -s tests -v
```

The benchmark writes metrics and top-3 traces to `results/`. Audit labels must be reviewed against the source PDFs before submission. The five evaluation dimensions and submission requirements are described in the root `BENCHMARK.md`, `GUIDE.md`, and `SUBMISSION.md`.

## Start the chat demo

```powershell
D:\miniconda3\python.exe -m src.app
```

Open `http://127.0.0.1:5050`. Chat answers use Mistral and cite the source PDF, page, and bounding box so the page can open beside the answer.