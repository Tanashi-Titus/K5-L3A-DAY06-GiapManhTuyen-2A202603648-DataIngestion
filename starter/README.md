# Starter · PostgreSQL + pgvector

Bộ khởi động **tùy chọn** cho lab cá nhân. Docker Compose tạo PostgreSQL + pgvector local; mã trong `src/` có pipeline OCR, Chroma và benchmark; xem phần triển khai bên dưới để biết trạng thái kiểm chứng thực tế. Vẫn có thể chọn Qdrant, Chroma hoặc vector store tương đương theo [GUIDE.md](../GUIDE.md).

## Cấu trúc

```text
starter/
├── docker-compose.yml     # PostgreSQL 16 + pgvector, chỉ mở cổng local
├── init.sql               # bật extension khi tạo database mới
├── requirements.txt       # psycopg, pypdf và python-dotenv
├── .env.example           # cấu hình mẫu; copy thành .env
├── scripts/check_setup.py # kiểm tra kết nối và extension (đã chạy được)
├── src/
│   ├── models.py          # cấu trúc dữ liệu mẫu
│   ├── ingestion.py       # TODO: đọc / chuẩn hóa tài liệu
│   ├── chunking.py        # TODO: chia chunk
│   ├── embeddings.py      # TODO: chọn model API hoặc local
│   ├── store.py           # TODO: lưu vector, metadata và filter
│   ├── evaluation.py      # TODO: chấm truy xuất, lưu trace
│   └── run.py             # TODO: kết nối các bước thành pipeline
├── data/                  # bạn tự chuẩn bị corpus được phép sử dụng
└── results/               # lưu kết quả của bạn
```

## 1. Cài và kiểm tra database

Cần Docker Desktop hoặc Docker Engine + Compose, Miniconda tại `D:\miniconda3`, và mạng để tải image/dependencies lần đầu. Trong workspace này dùng Miniconda base làm môi trường Python duy nhất; không tạo `.venv` riêng. Các lệnh chạy từ thư mục `starter/`:

```bash
D:\miniconda3\python.exe -m pip install -r requirements.txt
# macOS/Linux: cp .env.example .env
# Windows PowerShell: Copy-Item .env.example .env
docker compose -p day6_student_starter up -d --wait
D:\miniconda3\python.exe scripts/check_setup.py
```

Kỳ vọng: hiện tên database, phiên bản PostgreSQL và pgvector, sau đó `Setup OK`. Đây **chỉ là kiểm tra hạ tầng**, không phải kết quả benchmark. Docker dùng cổng `127.0.0.1:55433` và mật khẩu cố định **chỉ dùng local cho lab**; nếu cổng bận, sửa đồng thời port trong `docker-compose.yml` và `DATABASE_URL` trong `.env`. `init.sql` chỉ chạy khi volume mới được tạo; nếu database sẵn có chưa bật extension, xem log Docker và kiểm tra cấu hình thay vì xóa volume chứa dữ liệu.

Dừng container nhưng giữ dữ liệu:

```bash
docker compose -p day6_student_starter stop
```

## 2. Chọn embedding model

Điền key tương ứng trong `.env` nếu dùng OpenRouter, OpenAI hoặc Gemini; **không commit `.env`**. Model local không cần API key. `requirements.txt` là dependencies của starter pgvector cũ; pipeline Chroma dùng `requirements-app.txt`. Nếu dùng provider khác: tự cài SDK hoặc thư viện local phù hợp với model bạn chọn và ghi lại version/lệnh cài trong báo cáo. Ghi tên model và số chiều; dùng cùng model cho toàn bộ chiến lược và vector query tương thích vector document.

## 3. Hoàn thiện pipeline

1. Đặt corpus vào `data/` hoặc cung cấp manifest/hướng dẫn truy cập. Đọc [GUIDE.md](../GUIDE.md) về **30 trang nội dung**, quyền dữ liệu và metadata.
2. Hoàn thiện từng hàm TODO trong `src/`. Lưu ID tài liệu, nguồn, trang/vị trí và ít nhất một trường filter có ích.
3. Xây ít nhất ba cấu hình; ví dụ A fixed-size, B theo đoạn, C như B nhưng có filter. Cần cùng corpus, model và benchmark; nạp lại không nhân đôi và xử lý chunk cũ khi dữ liệu đổi.
4. Tự viết ít nhất 20 câu hỏi kèm evidence, tách dev/test trước khi thử theo [BENCHMARK.md](../BENCHMARK.md). Lưu trace top-3 và báo cáo đủ năm tiêu chí.
5. Xem phần triển khai bên dưới; dùng `D:\miniconda3\python.exe -m src.run` cho các lệnh ingest, benchmark và select.

Lưu code, cấu hình, kết quả và lệnh chạy để người chấm tái lập; không commit key, dữ liệu mật hoặc dữ liệu không có quyền chia sẻ.

## OCR cho PDF scan

PDF scan cần OCR trước khi chia chunk. `src.ocr` dùng bộ phát hiện dòng RapidOCR và PaddleOCR `latin_PP-OCRv5_mobile_rec` để nhận dạng từng dòng tiếng Việt. Model PaddleOCR này chỉ nhận dạng dòng; hai thành phần đều cần thiết. Model có thể nhận dạng sai, nhất là chữ viết tay: phải đối chiếu với tài liệu gốc trước khi dùng làm gold evidence. Cần model PaddleOCR local và chỉ định thư mục bằng `--weights`; tự tải model đã bị tắt theo yêu cầu. Khi cần OCR, tiếp tục dùng Miniconda base đã chọn; không tạo thêm environment. Corpus hiện tại `data.pdf` có text layer nên không cần OCR.

Ví dụ tổng quát cho một file scan tên `scan.pdf`, chạy từ thư mục `starter/`:

```powershell
D:\miniconda3\python.exe -m pip install -r requirements-ocr.txt
D:\miniconda3\python.exe -m src.ocr ../data/scan.pdf --weights ../results/models/latin_PP-OCRv5_mobile_rec_infer --pages 1 2 --output ../results/ocr-sample.json
# Sau khi kiểm tra mẫu, chạy cả tài liệu:
D:\miniconda3\python.exe -m src.ocr ../data/scan.pdf --weights ../results/models/latin_PP-OCRv5_mobile_rec_infer --output ../results/ocr.json
```

Dùng `--device cuda` nếu PyTorch có CUDA phù hợp; mặc định chạy CPU. Kết quả JSON ghi số trang vật lý bắt đầu từ 1, kích thước trang và từng dòng với `id`, `text`, `bbox=[x0,y0,x1,y1]` tính bằng PDF points từ góc trên trái của trang hiển thị. File được ghi an toàn sau mỗi trang; thêm `--resume` để tiếp tục và kiểm tra SHA-256 của PDF cùng DPI, mặc định chạy lại sẽ ghi đè output. Kiểm tra số trang có nội dung và lỗi OCR; không mặc định 39 trang đều hợp lệ.

Corpus dùng `data/data.pdf` làm nguồn chính (28 trang nội dung) và bài báo CC BY 4.0 `data/quantum-oscillator.pdf` làm nguồn bổ sung (13 trang nội dung): 41 trang nội dung tổng cộng. Hai PDF có text layer; OCR không cần thiết. Loader giữ source ID, trang và bbox để mỗi citation mở đúng file.

## Triển khai pipeline và demo

Từ `starter/`, dùng Miniconda base duy nhất:

```powershell
D:\miniconda3\python.exe -m pip install -r requirements-app.txt
Copy-Item .env.example .env
# Add MISTRAL_API_KEY to starter/.env; keep that file local.
D:\miniconda3\python.exe -m src.run ingest --pdf ../data/data.pdf --pdf ../data/quantum-oscillator.pdf --document-id arxiv-1204.0653-v1 --document-id mdpi-entropy-2023-25-213 --source data/data.pdf --source data/quantum-oscillator.pdf --metadata ../data/data_pdf_page_metadata.json --metadata ../data/quantum_oscillator_page_metadata.json
D:\miniconda3\python.exe -m src.app
```

Mở `http://127.0.0.1:5050`. `src.app` đọc `MISTRAL_API_KEY` và `MISTRAL_MODEL` từ `starter/.env`; model cấu hình cho demo là `ministral-8b-latest`. API chỉ gửi câu hỏi và top-3 chunks tới Mistral. Mỗi citation chứa source ID, tên PDF, trang và bbox; bấm citation sẽ mở đúng file nguồn ở cột phải. Đã smoke test status, route trang PDF supplement và chat HTTP 200.

`data/data.pdf` là corpus local và bị loại khỏi Git do quyền tái phân phối chưa xác minh. Tải đúng bản arXiv v1 từ `https://arxiv.org/pdf/1204.0653v1` vào `data/data.pdf`; SHA-256 cần khớp trường `sha256` trong `data/manifest.json`. Metadata trang nằm trong `data/data_pdf_page_metadata.json`; filter C dùng `section`. `results/` chứa chunk, vector, thống kê và Chroma PersistentClient với metric cosine. EmbeddingGemma 2 chạy local, vector 768 chiều, `Document` cho tài liệu và `SearchQuery` cho query. Theo GUIDE, pages chỉ gồm nội dung; trang bibliography bị loại khỏi indexing. Corpus page counts và giấy phép được ghi trong `data/corpus_manifest.json`.

`benchmark/questions.json` có 20 câu trên hai nguồn (15 dev, 5 test), có 7 câu filter và mọi exact evidence đều được xác minh trên đúng trang PDF. Test mới dùng bài CC BY bổ sung. Filter C dùng giá trị `section` trong page metadata của từng PDF.

```powershell
D:\miniconda3\python.exe -m src.run benchmark --benchmark ../benchmark/questions.json --split dev
D:\miniconda3\python.exe -m src.run select --strategy C --rationale "Dev: Hit@3 hòa 8/15; C thắng Hit@1 với 6/15"
D:\miniconda3\python.exe -m src.run benchmark --benchmark ../benchmark/questions.json --split test
D:\miniconda3\python.exe -m unittest discover -s tests -v
```

Lần chạy hiện tại chọn C theo dev: Hit@3 8/15 (hòa), Hit@1 6/15; test: B/C đạt 3/5 Hit@1 và Hit@3, A đạt 2/5. Đây là mẫu test nhỏ, không khẳng định tốt hơn nói chung. Metrics, trace, stats và manual audits nằm trong `../results/`.

EmbeddingGemma 2 dùng `sentence-transformers` và `transformers` đã cài trong Miniconda base `D:\miniconda3\python.exe` (Python 3.13.2). Máy khác cần đặt `EMBEDDING_MODEL` tới bản model cục bộ tương thích 768 chiều. Không tạo/activate môi trường Python thứ hai cho project này.

`D:\miniconda3\python.exe -m src.audit` tạo hoặc cập nhật mẫu 10 vị trí coherence (5 mỗi nguồn) và 5 câu test cho metadata/grounding. Các nhãn thủ công của lần chạy hiện tại nằm trong `../results/audit_coherence.json` và `../results/audit_test.json`; lệnh giữ nguyên điểm đã có, trừ khi truyền `--reset`.

Đã chạy ingest, dev, khóa strategy, test, audit và unit tests bằng Miniconda base. Xem `../report/individual/TRANG_THAI.md` để biết kết quả và giới hạn của corpus.
