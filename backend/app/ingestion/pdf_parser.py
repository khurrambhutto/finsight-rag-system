"""Convert PDF content into page-grounded passages."""
from docling.document_converter import DocumentConverter
from docling_core.types.doc import TableItem, TextItem

MAX_TEXT_LENGTH = 1800


def split_text(text: str, limit: int = MAX_TEXT_LENGTH) -> list[str]:
    """Split long text at word boundaries, retaining every character of content."""
    parts = []
    text = text.strip()
    while len(text) > limit:
        cut = text.rfind(' ', 0, limit + 1)
        if cut < limit // 2:
            cut = limit
        parts.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        parts.append(text)
    return parts


def extract_passages(path):
    result = DocumentConverter().convert(path)
    if str(result.status.value) != 'success':
        raise ValueError(f'Document conversion did not complete successfully: {result.status.value}')
    document = result.document
    section = None
    passages = []
    for item, _ in document.iterate_items():
        if not isinstance(item, (TextItem, TableItem)):
            continue
        pages = {p.page_no for p in item.prov}
        # An item spanning pages cannot be assigned accurately to one page.
        if len(pages) != 1:
            continue
        page = next(iter(pages))
        if isinstance(item, TableItem):
            text = item.export_to_markdown(doc=document).strip()
            if text:
                passages.append({'page': page, 'section': section, 'content_type': 'table', 'text': text})
        else:
            text = item.text.strip()
            label = str(item.label.value)
            if label in ('section_header', 'title'):
                section = text or section
            if label in ('page_header', 'page_footer'):
                continue
            for part in split_text(text):
                passages.append({'page': page, 'section': section, 'content_type': 'heading' if label in ('section_header', 'title') else 'text', 'text': part})
    if not passages:
        raise ValueError('No page-grounded content was extracted from this PDF.')
    return passages
