# Đối chiếu yêu cầu Day 06

Corpus có hai nguồn: `data/data.pdf` là nguồn chính (arXiv:1204.0653v1), cộng bài báo về quantum oscillator được cấp CC BY 4.0. Cấu hình, số trang và cách đếm nằm trong `data/corpus_manifest.json`. Kết quả được tạo bằng Miniconda base ngày 2026-11-13.

| Yêu cầu | Minh chứng / kết quả | Trạng thái |
|---|---|---|
| Tối thiểu 30 trang nội dung | 44 trang vật lý; loại 3 trang chỉ có references; còn **41 trang nội dung** (28 từ nguồn chính + 13 nguồn bổ sung). | **Đạt** |
| Nguồn, version, giấy phép, truy cập | Corpus manifest ghi source ID, title, author, URL/DOI, version, pages, SHA-256 và license. Supplement là CC BY 4.0. | Đã ghi. Quyền tái phân phối nguồn arXiv chính cần xác minh; `data/data.pdf` được giữ local/ignore bởi Git. |
| Parse, chuẩn hóa, lỗi và vị trí | PyMuPDF đọc text layer; không cần OCR. Loader chuẩn hóa Unicode/whitespace và lưu PDF source, document ID, số trang, line ID, bbox, page dimensions. | Đạt; 41/41 trang nội dung có text. |
| Ba cấu hình chunk | A fixed 500 chars / overlap 50; B block/paragraph tối đa 500; C dùng B và thêm metadata filter khi có filter input. | A: 248; B/C: 275 chunks. |
| Embedding thật, cùng model | EmbeddingGemma 2 local, 768 chiều; `Document` cho tài liệu, `SearchQuery` cho query; L2 normalization, cosine. Không gọi API embedding. | Đạt; vectors 248/275/275, tạo bằng `D:\miniconda3\python.exe`. |
| Vector database bền vững | Chroma PersistentClient, cosine, `results/chroma`, `day06-a/b/c`. | Đạt; collections 248/275/275, nạp lại thay collection cũ thay vì nhân đôi. |
| Metadata và filter hữu ích | `document_id`, `source`, `page`, `section`, `document_type`, `language`; `section` được gán theo heading/page map của từng PDF. | Đạt; filter C theo `section`; test audit metadata đúng/đủ **45/45 hits**. C tuân thủ filter **9/9 filtered test hits**. |
| Benchmark đã chuẩn bị trước khi chạy | `benchmark/questions.json`: 20 câu, 15 dev / 5 test; 7 câu có filter, gồm 3 test; exact evidence kiểm tra khớp trang PDF trước retrieval. Test mới chỉ hỏi nguồn bổ sung. | Đạt; trace giữ top-3, score và metadata. |
| Retrieval accuracy — dev | `results/metrics_dev.json`: A Hit@1 **4/15**, Hit@3 **8/15**; B **5/15**, **8/15**; C **6/15**, **8/15**. | Chọn **C**: Hit@3 hòa, Hit@1 cao nhất trên dev. Lựa chọn được ghi trước khi chạy test. |
| Retrieval accuracy — test | `results/metrics_test.json`: A Hit@1 **2/5**, Hit@3 **2/5**; B **3/5**, **3/5**; C **3/5**, **3/5**. | Đã chạy. B/C tốt hơn A trên mẫu test nhỏ; không đổi lựa chọn sau khi xem test. |
| Chunk coherence | `results/audit_coherence.json`: 10 vị trí cố định — 5 trang đầu hữu ích từ mỗi PDF; cùng vị trí giữa các strategy. Nhãn 0–2 hiện là bản nháp do Codex hỗ trợ, chưa được học viên xác nhận. | Sơ bộ: A **14/20 (1.4/2)**; B **15/20 (1.5/2)**; C **15/20 (1.5/2)**. Cần học viên đối chiếu và xác nhận từng vị trí trước khi nộp. |
| Grounding quality | `results/audit_test.json`: điểm của top-3 cho 5 câu test/strategy hiện là bản nháp do Codex hỗ trợ; đây là grounding của evidence, không phải độ chính xác LLM. | Sơ bộ: A: điểm 0/1/2 = **1/1/3**, trung bình **1.4/2**. B/C = **0/1/4**, trung bình **1.8/2**. Học viên cần rà soát cùng trace và PDF trước khi coi là audit thủ công hoàn tất. |
| Tác động của strategy | A–B thay cách chia chunk; B–C giữ nguyên chunks/vectors, đổi metadata filter. | Dev ưu tiên C; test B và C bằng nhau. Filter giúp 1 Hit@1 trên dev so với B, nhưng không đổi test. Mẫu nhỏ nên chỉ kết luận trong corpus này. |
| Chat Mistral và PDF citation | `starter/src/app.py`, `starter/web/index.html`; Mistral `ministral-8b-latest`; citation mang source ID/file/page/boxes. | Đã smoke test: web/status/PDF supplement/chat HTTP **200**; chat trích dẫn cả `quantum-oscillator.pdf` trang 7 và nguồn chính, có bbox. |
| Unit tests và kiểm tra mã | `starter/tests/test_pipeline.py`; lệnh `git diff --check`. | **5/5 unit tests passed**, không có whitespace errors. |
| Thời gian / chi phí | `results/ingestion_stats.json`, chạy CPU Miniconda; local embedding, Chroma persistent. | Ingest **412.95 giây**; API embedding cost **0**. Thời gian sẽ khác tùy máy. |

## Chạy lại

Chạy từ `starter/`; project dùng một Python duy nhất là Miniconda base Python 3.13.2 tại `D:\miniconda3\python.exe`.

```powershell
D:\miniconda3\python.exe -m src.run ingest --pdf ..\data\data.pdf --pdf ..\data\quantum-oscillator.pdf --document-id arxiv-1204.0653-v1 --document-id mdpi-entropy-2023-25-213 --source data/data.pdf --source data/quantum-oscillator.pdf --metadata ..\data\data_pdf_page_metadata.json --metadata ..\data\quantum_oscillator_page_metadata.json
D:\miniconda3\python.exe -m src.run benchmark --benchmark ..\benchmark\questions.json --split dev
D:\miniconda3\python.exe -m src.run select --strategy C --rationale "Dev: Hit@3 hòa 8/15; C đạt Hit@1 cao nhất 6/15"
D:\miniconda3\python.exe -m src.run benchmark --benchmark ..\benchmark\questions.json --split test
D:\miniconda3\python.exe -m src.audit
D:\miniconda3\python.exe -m unittest discover -s tests -v
```

## Ghi chú trước khi push

`starter/.env` bị ignore và chứa API key; không commit key. `data/data.pdf` cũng bị ignore do quyền tái phân phối chưa được xác minh. Hướng dẫn và SHA-256 để lấy đúng bản arXiv nằm trong `starter/README.md` và `data/manifest.json`. PDF supplement CC BY 4.0, có attribution và source trong corpus manifest. Git hiện không bao gồm các PDF cũ của Nghị định 13 hay artifacts OCR của lần thử trước.
