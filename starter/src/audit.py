"""Prepare reproducible, unscored templates for the required human audit."""
import json
import argparse
from pathlib import Path
from .run import ROOT, RESULTS
from .ingestion import load_pdf
from .chunking import fixed_size, by_paragraph


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reset',action='store_true',help='Replace existing audit files with blank templates')
    args=parser.parse_args()
    sources=[
        (ROOT/'data'/'data.pdf','arxiv-1204.0653-v1','data/data.pdf',ROOT/'data'/'data_pdf_page_metadata.json'),
        (ROOT/'data'/'quantum-oscillator.pdf','mdpi-entropy-2023-25-213','data/quantum-oscillator.pdf',ROOT/'data'/'quantum_oscillator_page_metadata.json')]
    pages=[]
    for path,document_id,source,metadata_path in sources:
        source_pages=load_pdf(path,document_id,source)
        page_metadata=json.loads(metadata_path.read_text(encoding='utf-8'))
        for page in source_pages: page.metadata.update(page_metadata.get(str(page.page),{}))
        pages.extend([p for p in sorted(source_pages,key=lambda p:p.page)
                      if p.text and p.metadata.get('page_type')!='references'][:5])
    coherence=[]
    for page in pages:
        # Pick a reproducible substantive line, independent of retrieval scores.
        line = next((line for line in page.metadata['lines'] if len(line['text']) >= 40), page.metadata['lines'][0])
        for strategy in ('A','B','C'):
            chunks=fixed_size(page,500,50) if strategy=='A' else by_paragraph(page,500)
            chunk=next((c for c in chunks if any(span['line_id']==line['id'] for span in c.metadata['spans'])),None)
            if chunk:
                coherence.append({'strategy':strategy,'document_id':page.document_id,'source':page.source,'page':page.page,'line_id':line['id'],
                    'chunk_id':chunk.chunk_id,'chunk_text':chunk.text,'score':None,'reason':''})
    coherence_path=RESULTS/'audit_coherence.json'
    if args.reset or not coherence_path.exists():
        coherence_path.write_text(json.dumps(coherence,ensure_ascii=False,indent=2),encoding='utf-8')
    traces=json.loads((RESULTS/'trace_test.json').read_text(encoding='utf-8'))
    audits=[]
    for trace in traces:
        audits.append({'strategy':trace['strategy'],'question_id':trace['question']['id'],
            'grounding_score':None,'grounding_reason':'',
            'metadata_checks':[{'chunk_id':h['chunk_id'],'correct_and_complete':None,'reason':''} for h in trace['hits']],
            'filter_compliant':None,'filter_reason':''})
    audit_path=RESULTS/'audit_test.json'
    if args.reset or not audit_path.exists():
        audit_path.write_text(json.dumps(audits,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Prepared template data for {len(coherence)} coherence and {len(audits)} test audit rows; existing scores are preserved (use --reset to clear them).')

if __name__=='__main__': main()
