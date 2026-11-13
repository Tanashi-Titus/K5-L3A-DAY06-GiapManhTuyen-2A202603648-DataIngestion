import unittest
from src.models import DocumentPage
from src.chunking import fixed_size, by_paragraph
from src.evaluation import evaluate_query, summarize

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.page=DocumentPage('doc','doc.pdf',1,'Alpha beta\nGamma delta',{'lines':[
            {'id':'l1','text':'Alpha beta','bbox':[0,0,10,5]},
            {'id':'l2','text':'Gamma delta','bbox':[0,6,10,11]}], 'page_width':20, 'page_height':20})

    def test_chunk_spans_point_to_matching_lines(self):
        for chunk in fixed_size(self.page, 15, 3)+by_paragraph(self.page, 15):
            self.assertLessEqual(len(chunk.text),15)
            for span in chunk.metadata['spans']:
                source=next(l for l in self.page.metadata['lines'] if l['id']==span['line_id'])
                self.assertIn(chunk.text[span['start']:span['end']],source['text'])
                self.assertEqual(span['bbox'],source['bbox'])

    def test_evidence_requires_page_source_and_quote(self):
        question={'gold_source_id':'doc','gold_page':1,'evidence_quote':'gamma delta','split':'dev'}
        hits=[{'document_id':'wrong','page':1,'text':'Gamma delta'}, {'document_id':'doc','page':1,'text':'Gamma delta'}]
        trace=evaluate_query(question,hits)
        self.assertFalse(trace['hit1']); self.assertTrue(trace['hit3'])
        self.assertEqual(summarize([{'strategy':'A',**trace}])[0]['hit3_n'],1)

if __name__=='__main__': unittest.main()

class AppTests(unittest.TestCase):
    def test_citations_link_only_used_evidence_to_boxes(self):
        import io
        from unittest.mock import patch
        import src.app as web
        class Embedder:
            def embed_query(self, text): return [1.0]
        class Store:
            def search(self,*args,**kwargs):
                return [{'document_id':'doc','source':'source.pdf','page':2,'text':'evidence','metadata':{'page_width':100,'page_height':200,
                    'spans':[{'bbox':[1,2,30,4]}]}}]
        web._embedder,web._store=Embedder(),Store()
        response=io.BytesIO(b'{"choices":[{"message":{"content":"Cau tra loi [1]"}}]}')
        try:
            with patch.dict('os.environ', {'MISTRAL_API_KEY':'test-key'}), patch.object(web,'urlopen',return_value=response) as call:
                result=web.app.test_client().post('/api/chat',json={'question':'Test'})
                self.assertEqual(call.call_args.args[0].full_url, 'https://api.mistral.ai/v1/chat/completions')
            self.assertEqual(result.status_code,200)
            self.assertEqual(result.json['citations'][0]['document_id'],'doc')
            self.assertEqual(result.json['citations'][0]['source'],'source.pdf')
            self.assertEqual(result.json['citations'][0]['page'],2)
            self.assertEqual(result.json['citations'][0]['boxes'],[[1,2,30,4]])
        finally:
            web._embedder=web._store=None

    def test_supplement_pdf_page_route(self):
        import src.app as web
        result=web.app.test_client().get('/api/page/mdpi-entropy-2023-25-213/3')
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.mimetype,'image/png')

    def test_missing_key_returns_clear_error(self):
        from unittest.mock import patch
        import src.app as web
        with patch.dict('os.environ', {}, clear=True):
            result=web.app.test_client().post('/api/chat',json={'question':'Test'})
        self.assertEqual(result.status_code,503)
        self.assertIn('MISTRAL_API_KEY',result.json['error'])
