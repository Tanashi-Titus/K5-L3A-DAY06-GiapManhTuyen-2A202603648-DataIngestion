"""Download the VietOCR checkpoint in verified byte ranges, with atomic output."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

URL = 'https://vocr.vn/data/vietocr/vgg_transformer.pth'
TARGET = Path(__file__).resolve().parents[2] / 'results' / 'models' / 'vgg_transformer.pth'

def main():
    response = requests.head(URL, timeout=30)
    response.raise_for_status()
    total = int(response.headers['Content-Length'])
    parts = 8
    def fetch(index):
        start = total * index // parts
        end = total * (index+1) // parts - 1
        r = requests.get(URL, headers={'Range': f'bytes={start}-{end}'}, timeout=180)
        r.raise_for_status()
        if r.status_code != 206 or len(r.content) != end-start+1:
            raise RuntimeError(f'Invalid range {index}: status {r.status_code}, size {len(r.content)}')
        print(f'Part {index+1}/{parts} downloaded', flush=True)
        return r.content
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=parts) as pool:
        chunks = list(pool.map(fetch, range(parts)))
    tmp = TARGET.with_suffix('.part')
    with tmp.open('wb') as f:
        for chunk in chunks: f.write(chunk)
    if tmp.stat().st_size != total: raise RuntimeError('Incorrect model size')
    tmp.replace(TARGET)
    print(f'Complete: {total} bytes at {TARGET}')

if __name__ == '__main__': main()
