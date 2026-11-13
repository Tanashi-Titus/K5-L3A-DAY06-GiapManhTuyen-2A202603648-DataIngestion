"""Load OCR output with line-level source coordinates."""
import json
import re
import unicodedata
from pathlib import Path
from .models import DocumentPage


def normalize_text(text: str) -> str:
    return '\n'.join(re.sub(r'[^\S\n]+', ' ', line).strip() for line in unicodedata.normalize('NFC', text).splitlines()).strip()


def load_ocr(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    data = json.loads(path.read_text(encoding='utf-8'))
    pages = []
    for p in data['pages']:
        lines = []
        for line in p['lines']:
            text = normalize_text(line['text'])
            if text:
                lines.append({**line, 'text': text})
        pages.append(DocumentPage(document_id, source, p['page'], '\n'.join(x['text'] for x in lines),
                                  {'lines': lines, 'page_width': p['width'], 'page_height': p['height']}))
    return pages


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    import fitz
    pages = []
    with fitz.open(path) as doc:
        for p in doc:
            lines = []
            for block_index, block in enumerate(p.get_text('dict')['blocks']):
                for line_index, line in enumerate(block.get('lines', [])):
                    text = normalize_text(''.join(s['text'] for s in line['spans']))
                    if text:
                        lines.append({'id': f'p{p.number+1:04d}-l{len(lines)+1:04d}', 'text': text,
                                      'bbox': list(line['bbox']), 'paragraph_id': f'p{p.number+1:04d}-b{block_index:04d}',
                                      'paragraph_line': line_index})
            pages.append(DocumentPage(document_id, source, p.number+1, '\n'.join(l['text'] for l in lines),
                         {'lines': lines, 'page_width': p.rect.width, 'page_height': p.rect.height}))
    return pages
