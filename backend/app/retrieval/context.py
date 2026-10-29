"""Restore page-grounded source context after ranking small search segments."""
import re

MAX_TABLE_CONTEXT = 6000
MAX_TEXT_CONTEXT = 4000


def is_overview(question: str):
    return bool(re.search(r'\b(overview|summary|summari[sz]e)\b|\b(report|document)\b.*\b(about|covers?|contains?|discusses?)\b', question, re.I))


def table_context(text: str, matches: list[str]):
    if len(text) <= MAX_TABLE_CONTEXT:
        return text
    lines = text.splitlines()
    selected = set(range(min(3, len(lines))))
    size = sum(len(lines[index]) + 1 for index in selected)
    for match in matches:
        row = match.splitlines()[-1]
        for index, line in enumerate(lines):
            if line != row:
                continue
            for neighbor in [index, index - 1, index + 1]:
                if 0 <= neighbor < len(lines) and neighbor not in selected and size + len(lines[neighbor]) + 1 <= MAX_TABLE_CONTEXT:
                    selected.add(neighbor)
                    size += len(lines[neighbor]) + 1
    return '\n'.join(lines[index] for index in sorted(selected))


def text_context(chunks, index):
    source = chunks[index]
    selected = {index}
    size = len(source['text'])
    for neighbor in [index - 1, index + 1]:
        if not 0 <= neighbor < len(chunks):
            continue
        chunk = chunks[neighbor]
        if (chunk['page'] == source['page'] and chunk['section'] == source['section']
                and chunk['content_type'] != 'table' and size + len(chunk['text']) + 2 <= MAX_TEXT_CONTEXT):
            selected.add(neighbor)
            size += len(chunk['text']) + 2
    return '\n\n'.join(chunks[position]['text'] for position in sorted(selected))


def table_preface(chunks, index):
    source = chunks[index]
    parts = []
    size = 0
    for neighbor in range(index - 1, max(-1, index - 4), -1):
        chunk = chunks[neighbor]
        if (chunk['page'] != source['page'] or chunk['section'] != source['section']
                or chunk['content_type'] == 'table' or size + len(chunk['text']) > 1000):
            break
        parts.append(chunk['text'])
        size += len(chunk['text'])
    return '\n\n'.join(reversed(parts))


def select_passages(document, chunks, hits, question, limit):
    by_id = {chunk['id']: (index, chunk) for index, chunk in enumerate(chunks)}
    grouped = {}
    for hit in hits:
        grouped.setdefault(hit.payload['chunk_id'], []).append(hit)
    selected = []
    seen = set()
    if is_overview(question) and limit > 0:
        first_page = min(chunk['page'] for chunk in chunks)
        cover = [chunk for chunk in chunks if chunk['page'] == first_page and chunk['content_type'] != 'table']
        if cover:
            source = cover[0]
            text = '\n'.join(chunk['text'] for chunk in cover)
            if len(text) <= MAX_TEXT_CONTEXT:
                selected.append({'document_id': document['id'], 'chunk_id': source['id'], 'page': first_page,
                                 'section': source['section'], 'content_type': 'text', 'text': text, 'score': 0.0})
                seen.add(source['id'])
    for chunk_id, matches in grouped.items():
        if len(selected) >= limit:
            break
        if chunk_id in seen:
            continue
        index, source = by_id[chunk_id]
        if source['content_type'] == 'table':
            table = table_context(source['text'], [hit.payload['text'] for hit in matches])
            text = '\n\n'.join(part for part in [table_preface(chunks, index), table] if part)
        else:
            text = text_context(chunks, index)
        selected.append({'document_id': document['id'], 'chunk_id': chunk_id, 'page': source['page'],
                         'section': source['section'], 'content_type': source['content_type'], 'text': text,
                         'score': matches[0].score})
        seen.add(chunk_id)
    return selected
