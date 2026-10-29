"""Persist a document's extracted passages as one atomic processing result."""
import logging
import uuid
from app.main import connect, REPORTS

logger = logging.getLogger(__name__)


def process_document(document_id: str):
    try:
        from app.ingestion.pdf_parser import extract_passages
        passages = extract_passages(REPORTS / f'{document_id}.pdf')
        with connect() as db:
            db.execute('DELETE FROM chunks WHERE document_id = ?', (document_id,))
            db.executemany('INSERT INTO chunks (id, document_id, page, section, content_type, text, position) VALUES (?, ?, ?, ?, ?, ?, ?)', [
                (str(uuid.uuid4()), document_id, p['page'], p['section'], p['content_type'], p['text'], index)
                for index, p in enumerate(passages)
            ])
            db.execute("UPDATE documents SET status = 'ready', error = NULL WHERE id = ?", (document_id,))
    except Exception as exc:
        logger.exception('Failed to process document %s', document_id)
        with connect() as db:
            db.execute("UPDATE documents SET status = 'failed', error = ? WHERE id = ?", (str(exc)[:500], document_id))
