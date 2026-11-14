"""Ingest text-based PDFs and run a locked dev/test retrieval benchmark."""
import argparse
import json
import sys
import time
from pathlib import Path
from .ingestion import load_pdf
from .chunking import fixed_size, by_paragraph
from .evaluation import evaluate_query, summarize
from .embeddings import MyEmbedder, default_model
from .store import ChromaStore

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / 'results'
MODEL = default_model()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def ingest(args):
    start = time.perf_counter()
    if args.pdf:
        pdfs = args.pdf if isinstance(args.pdf, list) else [args.pdf]
        ids = args.document_id or []
        sources = args.source or []
        metadata_files = args.metadata or []
        pages = []
        documents = []
        for i, pdf in enumerate(pdfs):
            document_id = ids[i] if i < len(ids) else Path(pdf).stem
            source = sources[i] if i < len(sources) else str(Path(pdf))
            document_pages = load_pdf(Path(pdf), document_id, source)
            metadata_path = Path(metadata_files[i]) if i < len(metadata_files) and metadata_files[i] else None
            page_metadata = json.loads(metadata_path.read_text(encoding='utf-8')) if metadata_path else {}
            for page in document_pages:
                page.metadata.update(page_metadata.get(str(page.page), {}))
            useful_pages = [p for p in document_pages if p.metadata.get('page_type') != 'references']
            pages.extend(useful_pages)
            documents.append({'document_id': document_id, 'source': source, 'physical_pages': len(document_pages),
                              'content_pages': len(useful_pages)})
    else:
        raise ValueError('Provide at least one --pdf')
    embedder = MyEmbedder(args.model)
    store = ChromaStore(args.store)
    stats = []
    shared_chunks = shared_vectors = None
    for strategy in ('A', 'B', 'C'):
        now = time.perf_counter()
        if strategy == 'C':
            chunks, vectors = shared_chunks, shared_vectors
        else:
            chunks = [c for p in pages for c in (fixed_size(p, 500, 50) if strategy == 'A' else by_paragraph(p, 500))]
            if not chunks: raise ValueError('The source did not provide any non-empty chunks')
            vectors = embedder.embed_documents([c.text for c in chunks])
            if strategy == 'B': shared_chunks, shared_vectors = chunks, vectors
        store.replace(strategy, chunks, vectors)
        stats.append({'strategy': strategy, 'chunks': len(chunks), 'characters': sum(len(c.text) for c in chunks),
                      'min_length': min(map(lambda c:len(c.text),chunks)), 'max_length': max(map(lambda c:len(c.text),chunks)),
                      'mean_length':round(sum(len(c.text) for c in chunks)/len(chunks),1),
                      'vectors':len(vectors), 'seconds': round(time.perf_counter()-now,2)})
    page_characters = {f'{p.document_id}:{p.page}':len(p.text) for p in pages}
    chunk_summary = {'documents':documents, 'physical_pages_total':sum(d['physical_pages'] for d in documents),
        'content_pages_total':sum(d['content_pages'] for d in documents), 'content_requirement_met':sum(d['content_pages'] for d in documents)>=30,
        'total_extracted_characters':sum(map(len,(p.text for p in pages))), 'page_characters':page_characters,
        'strategies':{s['strategy']:{k:s[k] for k in ('chunks','characters','min_length','max_length','mean_length','vectors')} for s in stats}}
    save(RESULTS/'chunk_stats.json', chunk_summary)
    save(RESULTS/'embedding_stats.json', {'model':args.model,'dimensions':embedder.dimensions,
        'normalization':'L2; cosine-compatible','environment':sys.executable,
        'storage':'Chroma persistent collections; raw vector dumps are not retained',
        **{s['strategy']:{'chunks':s['chunks'],'vectors':s['vectors'],
            **({'reuses':'B'} if s['strategy']=='C' else {})} for s in stats}})
    save(RESULTS/'chroma_stats.json', {'backend':'Chroma PersistentClient','path':args.store,'metric':'cosine',
        'collections':{s['strategy']:s['chunks'] for s in stats},'sources':[d['source'] for d in documents]})
    save(RESULTS/'ingestion_stats.json', {'model': args.model, 'dimensions': embedder.dimensions,
          'store': 'Chroma persistent, cosine', 'cost': 0, 'documents': documents, 'stats': stats,
          'total_seconds': round(time.perf_counter()-start,2), 'environment': r'D:\miniconda3\python.exe'})
    print(json.dumps(stats, ensure_ascii=False, indent=2))


def benchmark(args):
    questions = json.loads(Path(args.benchmark).read_text(encoding='utf-8'))
    stats = json.loads((RESULTS/'ingestion_stats.json').read_text(encoding='utf-8'))
    if stats['model'] != args.model:
        raise ValueError('Query embedding model must match the indexed model')
    if args.split == 'dev' and (RESULTS/'metrics_test.json').exists():
        raise ValueError('Test has already been observed; further tuning is not independent')
    if len(questions)<20 or sum(q['split']=='dev' for q in questions)<15 or sum(q['split']=='test' for q in questions)<5:
        raise ValueError('Benchmark requires at least 15 dev and 5 test questions')
    if sum(bool(q.get('filter')) for q in questions)<3 or not any(q.get('filter') and q['split']=='test' for q in questions):
        raise ValueError('At least 3 filtered questions, including one test, are required')
    if not all(q.get('evidence_verified') is True for q in questions):
        raise ValueError('Every evidence must be verified against the original PDF before running')
    if args.split == 'test' and not (RESULTS/'selected_strategy.json').exists():
        raise ValueError('Record the dev-selected strategy before running test')
    embedder, store = MyEmbedder(args.model), ChromaStore(args.store)
    traces = []
    for q in questions:
        if q['split'] != args.split: continue
        vector = embedder.embed_query(q['question'])
        for strategy in ('A','B','C'):
            hits = store.search(strategy, vector, filters=q.get('filter') if strategy == 'C' else None)
            traces.append({'strategy':strategy, **evaluate_query(q,hits)})
    save(RESULTS/f'trace_{args.split}.json', traces)
    save(RESULTS/f'metrics_{args.split}.json', summarize(traces))
    print(json.dumps(summarize(traces),ensure_ascii=False,indent=2))


def select(args):
    if not (RESULTS/'metrics_dev.json').exists(): raise ValueError('Run dev first')
    if (RESULTS/'metrics_test.json').exists(): raise ValueError('Test already viewed; selection is no longer independent')
    save(RESULTS/'selected_strategy.json', {'strategy':args.strategy,'rationale':args.rationale})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    ingest_p = sub.add_parser('ingest')
    ingest_p.add_argument('--pdf', action='append', required=True); ingest_p.add_argument('--document-id', action='append')
    ingest_p.add_argument('--source', action='append'); ingest_p.add_argument('--metadata', action='append')
    ingest_p.add_argument('--store', default=str(RESULTS/'chroma')); ingest_p.add_argument('--model', default=MODEL)
    ingest_p.set_defaults(func=ingest)
    bench = sub.add_parser('benchmark'); bench.add_argument('--benchmark',required=True); bench.add_argument('--split',choices=['dev','test'],required=True)
    bench.add_argument('--store',default=str(RESULTS/'chroma')); bench.add_argument('--model',default=MODEL); bench.set_defaults(func=benchmark)
    choose=sub.add_parser('select'); choose.add_argument('--strategy',choices=['A','B','C'],required=True); choose.add_argument('--rationale',required=True); choose.set_defaults(func=select)
    args=parser.parse_args(); args.func(args)

if __name__ == '__main__': main()
