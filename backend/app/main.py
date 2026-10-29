from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import os
import sqlite3
import uuid

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("FINSIGHT_DATA_DIR", ROOT / "data"))
REPORTS = DATA / "reports"
DATABASE = DATA / "finsight.db"


def connect():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    REPORTS.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY, filename TEXT NOT NULL, company TEXT NOT NULL,
            year INTEGER NOT NULL, uploaded_at TEXT NOT NULL, status TEXT NOT NULL
        )""")
        columns = {row['name'] for row in db.execute("PRAGMA table_info(documents)")}
        if 'error' not in columns:
            db.execute("ALTER TABLE documents ADD COLUMN error TEXT")
        db.execute("""CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY, document_id TEXT NOT NULL, page INTEGER NOT NULL,
            section TEXT, content_type TEXT NOT NULL, text TEXT NOT NULL, position INTEGER NOT NULL,
            FOREIGN KEY(document_id) REFERENCES documents(id)
        )""")
        db.execute("UPDATE documents SET status = 'failed', error = 'Processing was interrupted. Try again.' WHERE status = 'processing'")
    yield


app = FastAPI(title="FinSight AI", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST"], allow_headers=["*"])


@app.get("/documents")
def list_documents():
    with connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM documents ORDER BY uploaded_at DESC")]


@app.post("/documents", status_code=201)
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...), company: str = Form(...), year: int = Form(...)):
    company = company.strip()
    filename = Path((file.filename or "").replace("\\", "/")).name
    if not company or len(company) > 200:
        raise HTTPException(422, "Enter a company name (up to 200 characters).")
    if year < 1900 or year > datetime.now(timezone.utc).year + 1:
        raise HTTPException(422, "Enter a valid report year.")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(422, "Choose a PDF file.")
    document_id = str(uuid.uuid4())
    destination = REPORTS / f"{document_id}.pdf"
    try:
        with destination.open("wb") as output:
            first = await file.read(1024 * 1024)
            if not first.startswith(b"%PDF-"):
                raise HTTPException(422, "The file is not a valid PDF.")
            output.write(first)
            while chunk := await file.read(1024 * 1024):
                output.write(chunk)
        document = {"id": document_id, "filename": filename, "company": company, "year": year,
                    "uploaded_at": datetime.now(timezone.utc).isoformat(), "status": "pending"}
        with connect() as db:
            db.execute("INSERT INTO documents (id, filename, company, year, uploaded_at, status) VALUES (:id, :filename, :company, :year, :uploaded_at, :status)", document)
        schedule_processing(document_id, background_tasks)
        document["status"] = "processing"
        return document
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


def schedule_processing(document_id: str, background_tasks: BackgroundTasks):
    from app.ingestion.processing import process_document
    with connect() as db:
        result = db.execute("UPDATE documents SET status = 'processing', error = NULL WHERE id = ? AND status != 'processing'", (document_id,))
        if result.rowcount != 1:
            raise HTTPException(409, 'Document is already processing.')
    background_tasks.add_task(process_document, document_id)


@app.post('/documents/{document_id}/process', status_code=202)
def start_processing(document_id: str, background_tasks: BackgroundTasks):
    with connect() as db:
        if not db.execute('SELECT id FROM documents WHERE id = ?', (document_id,)).fetchone():
            raise HTTPException(404, 'Document not found.')
    schedule_processing(document_id, background_tasks)
    return {'status': 'processing'}


@app.get('/documents/{document_id}/chunks')
def get_chunks(document_id: str):
    with connect() as db:
        document = db.execute('SELECT id, company, year, status, error FROM documents WHERE id = ?', (document_id,)).fetchone()
        if not document:
            raise HTTPException(404, 'Document not found.')
        chunks = db.execute('SELECT id, document_id, page, section, content_type, text FROM chunks WHERE document_id = ? ORDER BY position', (document_id,)).fetchall()
        return {'document': dict(document), 'chunks': [dict(chunk) for chunk in chunks]}


@app.get('/documents/{document_id}/file')
def get_file(document_id: str):
    with connect() as db:
        document = db.execute('SELECT filename FROM documents WHERE id = ?', (document_id,)).fetchone()
    path = REPORTS / f'{document_id}.pdf'
    if not document or not path.is_file():
        raise HTTPException(404, 'Document not found.')
    return FileResponse(path, media_type='application/pdf', filename=document['filename'], content_disposition_type='inline')

from app.api.questions import router as questions_router
app.include_router(questions_router)
from app.api.models import router as models_router
app.include_router(models_router)
