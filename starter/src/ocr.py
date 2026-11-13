"""OCR scanned PDFs into traceable line-level JSON using local PaddleOCR."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path


def run(pdf_path: Path, output: Path, pages: list[int] | None, dpi: int, device: str, weights: Path | None = None, resume: bool = False) -> None:
    if weights is None or not all((weights / name).is_file() for name in ('inference.json','inference.pdiparams','inference.yml')):
        raise FileNotFoundError('Provide --weights pointing to a complete local PaddleOCR recognition model directory.')
    os.environ.setdefault('PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK', 'True')
    import fitz
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR
    from paddleocr import TextRecognition

    if dpi < 72 or dpi > 400:
        raise ValueError('DPI must be between 72 and 400')
    doc = fitz.open(pdf_path)
    selected = pages if pages is not None else list(range(1, len(doc) + 1))
    if not selected or any(p < 1 or p > len(doc) for p in selected):
        raise ValueError(f'Page numbers must be between 1 and {len(doc)}')
    detector = RapidOCR()
    recognizer = TextRecognition(model_name='latin_PP-OCRv5_mobile_rec', model_dir=str(weights.resolve()), device=device, enable_mkldnn=False)
    with pdf_path.open('rb') as source_file:
        source_hash = hashlib.file_digest(source_file, 'sha256').hexdigest()
    result = {'source': str(pdf_path), 'source_sha256': source_hash, 'page_count': len(doc), 'dpi': dpi,
              'detector': 'RapidOCR default text detector', 'recognizer': 'PaddleOCR latin_PP-OCRv5_mobile_rec',
              'coordinate_system': 'PDF page points, top-left origin, x right and y down', 'pages': []}
    if resume and output.exists():
        existing = json.loads(output.read_text(encoding='utf-8'))
        if existing.get('source_sha256') != source_hash or existing['dpi'] != dpi or existing['page_count'] != len(doc) or existing.get('recognizer') != result['recognizer']:
            raise ValueError('Existing OCR output is for a different PDF or DPI')
        result = existing
    completed = {p['page'] for p in result['pages']}
    for page_no in selected:
        if page_no in completed:
            print(f'Page {page_no}: already completed', flush=True)
            continue
        start = time.perf_counter()
        page = doc[page_no - 1]
        pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csRGB, alpha=False)
        rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        bgr = np.ascontiguousarray(rgb[:, :, ::-1])
        boxes, _ = detector.text_detector(bgr)
        lines = []
        if boxes is not None and len(boxes):
            boxes = detector.sorted_boxes(boxes)
            crops = detector.get_crop_img_list(bgr, boxes)
            predictions = recognizer.predict(crops, batch_size=8)
            for box, prediction in zip(boxes, predictions):
                text = prediction['rec_text'].strip()
                if not text:
                    continue
                xs, ys = box[:, 0], box[:, 1]
                # The rendered page may have a crop box or rotation; coordinates are
                # relative to the displayed page rectangle, just like the pixmap.
                bbox = [float(xs.min() * page.rect.width / pix.width),
                        float(ys.min() * page.rect.height / pix.height),
                        float(xs.max() * page.rect.width / pix.width),
                        float(ys.max() * page.rect.height / pix.height)]
                lines.append({'id': f'p{page_no:04d}-l{len(lines)+1:04d}', 'text': text,
                              'bbox': [round(v, 2) for v in bbox], 'confidence': float(prediction['rec_score'])})
        result['pages'].append({'page': page_no, 'width': page.rect.width, 'height': page.rect.height,
                                'lines': lines, 'text': '\n'.join(line['text'] for line in lines),
                                'seconds': round(time.perf_counter() - start, 2)})
        print(f'Page {page_no}: {len(lines)} lines', flush=True)
        # Preserve completed pages if a later page fails or the process is stopped.
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + '.tmp')
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(output)
    doc.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    parser.add_argument('--output', type=Path, default=Path('results/ocr.json'))
    parser.add_argument('--pages', type=int, nargs='+', help='Physical PDF pages, 1-based (default: all)')
    parser.add_argument('--dpi', type=int, default=200)
    parser.add_argument('--device', default='cpu', choices=['cpu', 'cuda'])
    parser.add_argument('--weights', type=Path, help='Path to local PaddleOCR recognition model directory (required)')
    parser.add_argument('--resume', action='store_true', help='Continue completed pages in an existing output')
    args = parser.parse_args()
    run(args.pdf, args.output, args.pages, args.dpi, args.device, args.weights, args.resume)


if __name__ == '__main__':
    main()
