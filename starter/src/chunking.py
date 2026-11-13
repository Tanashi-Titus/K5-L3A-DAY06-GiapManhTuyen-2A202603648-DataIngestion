"""Line-aware chunking that preserves the bounding boxes used in citations."""
import hashlib
from .models import Chunk, DocumentPage


def _chunk(page, text, spans, kind):
    digest = hashlib.sha256(f'{page.document_id}|{page.page}|{kind}|{spans[0]["start"]}|{text}'.encode('utf-8')).hexdigest()[:20]
    metadata = {k: v for k, v in page.metadata.items() if k != 'lines'}
    metadata['spans'] = spans
    return Chunk(digest, page.document_id, page.source, page.page, text, metadata)


def _lines(page):
    result, pos = [], 0
    for line in page.metadata.get('lines', []):
        text = line['text']
        result.append((pos, pos + len(text), line))
        pos += len(text) + 1
    return result


def _window(page, start, end, kind):
    spans = [{'line_id': l['id'], 'bbox': l['bbox'], 'start': max(a, start)-start, 'end': min(b, end)-start}
             for a,b,l in _lines(page) if a < end and b > start]
    if not spans:
        return None
    return _chunk(page, page.text[start:end], spans, kind)


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError('Require size > 0 and 0 <= overlap < size')
    chunks = []
    for start in range(0, len(page.text), size - overlap):
        chunk = _window(page, start, min(start + size, len(page.text)), 'fixed')
        if chunk: chunks.append(chunk)
        if start + size >= len(page.text): break
    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """Group complete PDF text blocks/paragraphs, respecting a maximum size."""
    if max_size <= 0: raise ValueError('max_size must be positive')
    lines = _lines(page)
    groups = []
    for a, b, line in lines:
        key = line.get('paragraph_id', line['id'])
        if groups and groups[-1][0] == key:
            groups[-1][2] = b
        else:
            groups.append([key, a, b])

    chunks, start, end = [], None, None
    for _, a, b in groups:
        if b - a > max_size:
            if start is not None:
                chunk = _window(page, start, end, 'paragraph')
                if chunk: chunks.append(chunk)
                start = end = None
            part = a
            while b - part > max_size:
                chunk = _window(page, part, part + max_size, 'paragraph')
                if chunk: chunks.append(chunk)
                part += max_size
            if part < b:
                start, end = part, b
            continue
        if start is not None and b - start > max_size:
            chunk = _window(page, start, end, 'paragraph')
            if chunk: chunks.append(chunk)
            start = None
        if start is None: start = a
        end = b
    if start is not None and start < end:
        chunk = _window(page, start, end, 'paragraph')
        if chunk: chunks.append(chunk)
    return chunks
