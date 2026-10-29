# FinSight AI — Project Plan

Here’s a complete plan you can follow to build the project. I’ll call it **FinSight AI** for now—you can change the name later.

The idea is to build a financial research assistant that answers questions from company reports, shows where its answers came from, and measures how well it performs.

## 1. What the finished project does

A user opens the website, uploads financial reports, and asks a question such as:

> “How did Microsoft’s revenue change between 2023 and 2024?”

The system finds the relevant figures, calculates the change, and displays:

- A clear answer.
- The figures used in the calculation.
- Citations to the reports and pages.
- An option to open those pages and check the evidence.

A second part of the project lets **you**, as the developer, run benchmark questions and compare different versions of the system.

The first version will use **documents you provide**. Automatic web search for reports can be a later feature.

## 2. The main system flow

There are two separate flows: one for preparing documents and one for answering questions.

### Document preparation

```text
Upload PDF
    ↓
Extract text, tables, and page numbers
    ↓
Split content into useful passages
    ↓
Generate embeddings
    ↓
Store passages and embeddings in Qdrant
```

An *embedding* is a numerical representation of a passage’s meaning. It lets your app find relevant text even if the user doesn’t use the exact words found in the report.

### Answering a question

```text
User asks a question
    ↓
Search the uploaded reports
    ↓
Select and rerank the most relevant passages
    ↓
Send the passages and question to an LLM
    ↓
Return an answer with citations
```

For questions involving calculations, add a calculator step after retrieving the figures.

---

## 3. Recommended tech stack

This stack builds on tools you already know.

| Part | Technology | Purpose |
|---|---|---|
| Frontend | **React + TypeScript** | Upload reports, ask questions, view answers and evaluation results |
| Backend | **Python + FastAPI** | Handle uploads, retrieval, generation, and evaluation |
| PDF processing | **Docling** | Extract report content, tables, and document structure |
| Embeddings | **Sentence Transformers** | Turn passages and questions into searchable vectors |
| Vector database | **Qdrant** | Store embeddings and retrieve relevant passages |
| Keyword search | **BM25 / Qdrant hybrid search** | Find exact terms such as company names and financial metrics |
| Reranking | **Sentence Transformers cross-encoder** | Reorder retrieved passages by relevance |
| LLM | **Ollama with a local open-weight model**, or an API model | Generate answers from retrieved evidence |
| Metadata | **SQLite** initially | Store document records, processing status, and evaluation runs |
| Evaluation | **Python scripts + FinanceBench** | Measure retrieval, answer quality, and citations |
| Deployment | **Docker Compose** | Run the app and Qdrant together locally |
| Version control | **Git + GitHub** | Track changes and showcase the project |

[Docling](https://docling.ai/formats/) supports PDF content including tables and document provenance. [Qdrant](https://qdrant.tech/documentation/quickstart/) can run locally with Docker and supports hybrid search.

**Model choice:** Start with a small embedding model and an LLM that runs comfortably on your machine. Local models can require significant RAM and may run slowly without a suitable GPU. An API model is a practical fallback for development; document which parts run locally and which send data to an external provider.

You can use LangGraph later if your workflow becomes complex. For the first version, ordinary Python functions will be easier to build and debug.

---

## 4. Where to get the data

### For development: public company reports

Download two or three annual reports for one company. Start with reports from the company’s investor relations website.

For example:

- [Microsoft annual reports](https://www.microsoft.com/investor/reports/ar25/)
- Select reports from different years so you can test questions that compare years.

Keep the original PDFs and record their company, report year, title, and source URL.

### For evaluation: FinanceBench

[FinanceBench’s public repository](https://github.com/patronus-ai/financebench) contains a public sample of **150 questions** with answers, evidence, and associated document information.

The benchmark includes different document types and question types, so inspect each example and obtain the associated report before running it. Check the repository’s terms before redistributing reports or benchmark data.

Start with a small subset, such as 10–20 questions. Add more once your pipeline works.

**Important:** Keep two groups of questions:

- **Development questions:** Use these while improving the app.
- **Final test questions:** Set these aside until your implementation choices are fixed.

This gives you a more honest result than repeatedly tuning your system on the same questions you report.

---

## 5. Build phases

### Phase 1: Project setup and document upload

**Goal:** Get a PDF from the browser into your backend.

Build:

- A React page with a PDF upload button.
- A FastAPI endpoint to accept the file.
- A local folder for uploaded reports.
- An SQLite record containing:
  - Document ID.
  - Filename.
  - Company and year, entered by the user.
  - Upload date.
  - Processing status: `pending`, `processing`, `ready`, or `failed`.

**Done when:** You can upload a report and see it listed in the app.

---

### Phase 2: Extract and prepare report content

**Goal:** Turn a report into searchable passages.

Build a document processing pipeline that:

1. Reads the PDF with Docling.
2. Extracts paragraphs, headings, and tables.
3. Splits content into manageable chunks.
4. Saves the source information with every chunk.

Each chunk should contain something like:

```json
{
  "chunk_id": "doc-123-chunk-45",
  "document_id": "doc-123",
  "company": "Microsoft",
  "year": 2024,
  "page": 52,
  "section": "Revenue",
  "content_type": "text",
  "text": "Extracted passage goes here."
}
```

For tables, keep their rows, columns, and headings together where possible. A number without its year, unit, or row heading can be misleading.

**Check carefully:** PDF viewer page numbers and printed page numbers can differ. Store the physical PDF page index consistently so your citation opens the right page.

**Done when:** You can inspect extracted passages and trace each one back to the correct PDF page.

---

### Phase 3: Build a basic RAG system

**Goal:** Answer a question from one report with a source.

Build:

1. Generate embeddings for the extracted chunks.
2. Store embeddings and chunk metadata in Qdrant.
3. Embed the user’s question.
4. Retrieve the most similar chunks.
5. Send the question and retrieved chunks to the LLM.
6. Ask the LLM to answer only from the provided evidence.
7. Return the answer and source information to the frontend.

At this stage, keep the interface simple:

- Select a report.
- Ask a question.
- Show the answer.
- Show retrieved passages and page numbers.

Also support an answer such as:

> “I couldn’t find enough information in the selected reports to answer this question.”

**Done when:** A user can ask a question about one report and verify the answer on the cited page.

---

### Phase 4: Establish your first benchmark

**Goal:** Measure your baseline before improving retrieval.

Create an evaluation script that:

1. Loads a small set of FinanceBench examples.
2. Finds which report each example needs.
3. Runs the question through your system.
4. Saves the generated answer and retrieved sources.
5. Compares the result against the expected answer and evidence.

Save results in JSON or CSV:

```json
{
  "question_id": "example-001",
  "question": "Example financial question",
  "expected_answer": "Expected answer",
  "generated_answer": "Your system's answer",
  "expected_evidence_page": 52,
  "retrieved_pages": [52, 53, 61],
  "answer_correct": true,
  "evidence_retrieved": true,
  "citation_supported": true,
  "latency_seconds": 4.2
}
```

Start with these measurements:

- **Evidence retrieval rate:** How often did the retrieved passages include the expected evidence?
- **Answer accuracy:** How often was the final answer correct?
- **Citation support:** How often did the cited passage actually support the answer?
- **Latency:** How long did each question take?

For numerical answers, compare values carefully: `5 million` and `5,000,000` mean the same thing, but `5 billion` does not. For more complex answers, manually review a sample. If you use an LLM to judge answers, clearly label it as an automated judge and check some judgments yourself.

**Done when:** You have a saved baseline report and examples of both successful and failed answers.

---

### Phase 5: Improve retrieval

**Goal:** Find more relevant evidence than the baseline.

Add two retrieval methods:

- **Dense search:** Finds passages with similar meaning.
- **Keyword search:** Finds exact terms, such as “operating income” or a company name.

Combine the results using **hybrid search**, then add a **reranker** that reorders the best candidates based on their relevance to the question.

[Qdrant’s hybrid search and reranking tutorial](https://qdrant.tech/documentation/tutorials-basics/reranking-hybrid-search/) demonstrates this pattern.

Compare the configurations using the same development questions:

| Configuration | What it uses |
|---|---|
| Baseline | Dense search |
| Version 2 | Dense + keyword search |
| Version 3 | Dense + keyword search + reranking |

Record the settings, model names, and results for each run. Don’t assume the more complex version is better—measure it.

**Done when:** You can explain whether each change helped, and show examples of questions where it helped or failed.

---

### Phase 6: Add calculations and better table handling

**Goal:** Answer questions that compare financial figures.

For questions such as:

> “What was the percentage increase in revenue from 2023 to 2024?”

Your system should:

1. Retrieve both figures and their sources.
2. Identify the units and years.
3. Use a small, controlled calculator function.
4. Display the calculation and citations.

For example:

```text
Percentage change = (2024 value - 2023 value) / 2023 value × 100
```

Do not execute arbitrary code generated by the model. Provide specific calculator operations such as addition, subtraction, division, and percentage change.

Add checks for:

- Missing figures.
- Different units, such as millions versus billions.
- A zero denominator.
- Figures from the wrong company or year.
- Tables whose headers were extracted incorrectly.

If the values cannot be verified, the app should explain what is missing.

**Done when:** The app answers a few hand-checked comparison questions and shows the numbers, calculation, and sources.

---

### Phase 7: Build the evaluation dashboard

**Goal:** Make your experiments easy to understand and present.

Add an evaluation page that shows:

- The selected benchmark subset.
- The retrieval and model configuration.
- Number of questions evaluated.
- Evidence retrieval rate.
- Answer accuracy.
- Citation support rate.
- Average or median response time.
- A table of individual questions and results.

For each failed question, show:

- Expected answer.
- Generated answer.
- Expected evidence.
- Retrieved passages.
- Your notes on why it failed.

You can start by generating a Markdown or CSV report. A dashboard is useful, but the evaluation itself matters more.

**Done when:** Someone reviewing your repository can reproduce a run and understand what the results mean.

---

### Phase 8: Local model option and final polish

**Goal:** Make the project easy to run and demonstrate.

Add:

- An option to use a locally hosted model through Ollama.
- A model configuration page or environment variables.
- Clear processing and error states.
- A PDF page viewer or links that open the cited page.
- Docker Compose setup.
- A sample set of questions.
- A short demo video.
- A clear README.

If you compare a local model with an API model, use the same question set and retrieval configuration. Report model names, hardware, latency, and any API cost. Don’t claim the entire system is private unless every component used for that run is local.

---

## 6. Suggested API endpoints

You don’t need all of these on day one. Start with upload and question answering.

```text
POST   /documents
       Upload a report and start processing it.

GET    /documents
       List reports and processing status.

GET    /documents/{document_id}
       Get details for one report.

GET    /documents/{document_id}/file
       Open the original PDF.

POST   /questions
       Ask a question against selected reports.

POST   /evaluations
       Start an evaluation using a saved configuration.

GET    /evaluations
       List evaluation runs.

GET    /evaluations/{run_id}
       Get metrics and individual results.
```

A question request could look like:

```json
{
  "question": "What was the company's revenue in 2024?",
  "document_ids": ["doc-123"],
  "retrieval_mode": "hybrid_reranked"
}
```

A response could include:

```json
{
  "answer": "The report states that revenue was ...",
  "citations": [
    {
      "document_id": "doc-123",
      "page": 52,
      "excerpt": "Relevant passage from the report."
    }
  ],
  "calculation": null,
  "model": "configured-model-name"
}
```

---

## 7. Suggested project structure

```text
finsight-ai/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── documents.py
│   │   │   ├── questions.py
│   │   │   └── evaluations.py
│   │   ├── ingestion/
│   │   │   ├── pdf_parser.py
│   │   │   └── chunking.py
│   │   ├── retrieval/
│   │   │   ├── embeddings.py
│   │   │   ├── search.py
│   │   │   └── reranker.py
│   │   ├── generation/
│   │   │   ├── llm.py
│   │   │   └── calculator.py
│   │   ├── evaluation/
│   │   │   ├── financebench.py
│   │   │   └── metrics.py
│   │   └── storage/
│   │       └── database.py
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       └── services/
│
├── data/
│   ├── reports/
│   └── evaluation/
│
├── docs/
│   ├── architecture.md
│   └── evaluation-results.md
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

Treat this as a starting point, not a rule. You can create files as you need them.

---

## 8. What to show on GitHub

A recruiter should be able to understand the project quickly. Your README should include:

1. **What problem the project solves.**
2. A screenshot or short demo video.
3. A diagram of the document and question flows.
4. The tech stack.
5. Setup instructions and hardware requirements.
6. Example questions.
7. Your evaluation method and results.
8. Known limitations.
9. Links to the datasets and report sources.

Keep evaluation outputs reproducible: include the question subset identifiers, configuration, model versions, and scripts needed to rerun them. Avoid committing API keys or datasets you don’t have permission to redistribute.

---

## 9. How to put it on your CV

After you’ve built and evaluated it, you can use wording like this:

> **FinSight AI — Financial Research Assistant** | Python, FastAPI, Qdrant, React, LLMs  
> - Built a RAG application that answers questions from financial reports and provides page-level citations.  
> - Implemented **[the retrieval methods you completed]** and evaluated them on **[number] FinanceBench questions**.  
> - Added **[calculation or local model feature]** and documented answer accuracy, evidence retrieval, and latency.

Replace the brackets with your actual work and measured results. You don’t need impressive numbers to make this worthwhile; a clear explanation of failures and improvements is valuable too.

## 10. Your first working session

To get started today, I’d do only these five things:

1. Create the GitHub repository and the FastAPI/React folders.
2. Download **one** public annual report.
3. Write a Python script that extracts its text and page numbers.
4. Print a few extracted passages and manually check them against the PDF.
5. Write five questions whose answers you can find in that report.

Once you trust the extracted content and page numbers, move on to embeddings and search. That gives the rest of the project a reliable foundation.
