"""Local chat demo: Mistral answers and Chroma citations mapped to the PDF."""
import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from flask import Flask, jsonify, request, send_file
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / 'starter' / '.env', override=False)

from .run import ROOT, RESULTS, MODEL

app = Flask(__name__, static_folder='../web', static_url_path='')
PDF = ROOT / 'data' / 'data.pdf'
PDFS = {'arxiv-1204.0653-v1': PDF,
        'mdpi-entropy-2023-25-213': ROOT / 'data' / 'quantum-oscillator.pdf'}
_embedder = None
_store = None

@app.get('/')
def index(): return app.send_static_file('index.html')

def render_page(document_id, page_no):
    import fitz
    from io import BytesIO
    pdf_path = PDFS.get(document_id)
    if not pdf_path or not pdf_path.exists(): return jsonify({'error':'Nguồn PDF không tồn tại'}), 404
    with fitz.open(pdf_path) as doc:
        if not 1 <= page_no <= len(doc): return jsonify({'error':'Trang không tồn tại'}), 404
        pix = doc[page_no-1].get_pixmap(dpi=144, alpha=False)
        return send_file(BytesIO(pix.tobytes('png')), mimetype='image/png')

@app.get('/api/page/<int:page_no>')
def page(page_no): return render_page('arxiv-1204.0653-v1', page_no)

@app.get('/api/page/<document_id>/<int:page_no>')
def source_page(document_id, page_no): return render_page(document_id, page_no)

@app.get('/api/status')
def status():
    import fitz
    documents={}
    for document_id, path in PDFS.items():
        if path.exists():
            with fitz.open(path) as doc: documents[document_id]={'page_count':len(doc),'source':path.name}
    return jsonify({'page_count':documents['arxiv-1204.0653-v1']['page_count'], 'documents':documents,
                    'indexed':(RESULTS/'ingestion_stats.json').exists(),
                    'model':os.environ.get('MISTRAL_MODEL') or 'mistral-small-latest', 'api_key_set':bool(os.environ.get('MISTRAL_API_KEY','').strip())})

@app.post('/api/chat')
def chat():
    global _embedder, _store
    data=request.get_json(silent=True) or {}
    question=str(data.get('question','')).strip()
    if not question or len(question)>2000: return jsonify({'error':'Nhập câu hỏi từ 1–2000 ký tự.'}), 400
    mistral_key = os.environ.get('MISTRAL_API_KEY', '').strip()
    if not mistral_key:
        return jsonify({'error':'Thiếu biến môi trường MISTRAL_API_KEY.'}), 503
    try:
        if _embedder is None:
            from .embeddings import MyEmbedder
            from .store import ChromaStore
            chosen_model=os.environ.get('EMBEDDING_MODEL') or MODEL
            stats=json.loads((RESULTS/'ingestion_stats.json').read_text(encoding='utf-8'))
            if stats['model'] != chosen_model: raise ValueError('Embedding model không khớp index')
            _embedder=MyEmbedder(chosen_model)
            _store=ChromaStore(str(RESULTS/'chroma'))
        chosen=json.loads((RESULTS/'selected_strategy.json').read_text(encoding='utf-8'))
        strategy=data.get('strategy',chosen['strategy'])
        if strategy not in ('A','B','C'): raise ValueError('Cấu hình không hợp lệ')
        filters=data.get('filter') if strategy=='C' else None
        hits=_store.search(strategy,_embedder.embed_query(question),filters=filters)
        if not hits: return jsonify({'answer':'Không tìm thấy bằng chứng trong tài liệu.', 'citations':[]})
        context='\n\n'.join(f'[{i}] Nguồn {Path(h["source"]).name}, trang {h["page"]}: {h["text"]}' for i,h in enumerate(hits,1))
        prompt=('Trả lời cùng ngôn ngữ với câu hỏi. Chỉ trả lời dựa vào các đoạn nguồn bên dưới. '
                'Nếu không đủ bằng chứng, nói rõ không đủ thông tin. '
                'Mỗi ý dựa trên nguồn phải có trích dẫn dạng [1], [2] hoặc [3]. Không tự tạo căn cứ.\n\n'
                +context+'\n\nCâu hỏi: '+question)
        payload=json.dumps({'model':os.environ.get('MISTRAL_MODEL') or 'mistral-small-latest',
                            'messages':[{'role':'user','content':prompt}], 'temperature':0, 'max_tokens':1200},ensure_ascii=False).encode('utf-8')
        req=Request('https://api.mistral.ai/v1/chat/completions',data=payload,
                    headers={'Content-Type':'application/json','Authorization':'Bearer '+mistral_key})
        with urlopen(req, timeout=90) as response: answer=json.load(response)['choices'][0]['message']['content']
        used={int(n) for n in re.findall(r'\[(\d+)\]',answer) if 1<=int(n)<=len(hits)}
        citations=[{'number':i,'document_id':h['document_id'],'source':h['source'],'page':h['page'],'text':h['text'],'boxes':[s['bbox'] for s in h['metadata'].get('spans',[])],
                    'width':h['metadata']['page_width'],'height':h['metadata']['page_height']} for i,h in enumerate(hits,1) if i in used]
        if not citations:
            answer += '\n\nKhông có trích dẫn hợp lệ trong câu trả lời; vui lòng kiểm tra nguồn.'
        return jsonify({'answer':answer,'citations':citations})
    except HTTPError as exc:
        hints={401:'MISTRAL_API_KEY không hợp lệ hoặc đã hết hạn.',
               403:'API key chưa có quyền gọi model này.',
               429:'Mistral đang giới hạn tốc độ hoặc tài khoản hết quota.',
               422:'Tên model hoặc nội dung request chưa hợp lệ.'}
        return jsonify({'error':f'Mistral HTTP {exc.code}. {hints.get(exc.code, "Kiểm tra cấu hình model và dịch vụ Mistral.")}'}), 502
    except (URLError, TimeoutError) as exc:
        return jsonify({'error':f'Không kết nối được Mistral ({type(exc).__name__}); kiểm tra mạng rồi thử lại.'}), 503
    except Exception as exc:
        return jsonify({'error':f'Không thể chạy truy xuất hoặc gọi Mistral ({type(exc).__name__}). Kiểm tra cấu hình.'}), 503

if __name__ == '__main__': app.run(host='127.0.0.1', port=5050, debug=False)
