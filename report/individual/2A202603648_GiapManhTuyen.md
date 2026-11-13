# Báo cáo cá nhân — Day 6

## Dữ liệu và pipeline

Corpus dùng hai bài báo về cơ học lượng tử. Nguồn chính là `data/data.pdf` và *Quantum Oscillator at Temperature T...*. Quy tắc đếm và thông tin từng nguồn nằm trong `data/corpus_manifest.json`. Ba trang chỉ có tài liệu tham khảo không được tính. Bản PDF arXiv do người dùng cung cấp chưa có giấy phép tái phân phối xác nhận, vì vậy `data/data.pdf` bị loại khỏi Git; người chấm cần lấy bản theo URL trong manifest và đối chiếu SHA-256.

Hai PDF có lớp văn bản, nên pipeline dùng PyMuPDF để trích xuất; OCR không nằm trong lần ingest này. Văn bản được chuẩn hóa Unicode và khoảng trắng. Mỗi chunk lưu `document_id`, `source`, số trang PDF vật lý, `section`, `document_type` và các trường truy vết cần cho citation. Số trang trong metadata là số trang tính từ 1 trong PDF, không phải số in trên trang của bài báo. Các trang nội dung có text được đưa vào index; manifest ghi trang bị loại.

Embedding dùng EmbeddingGemma 2 local, vector 768 chiều, chuẩn hóa L2 và so sánh cosine. Vector store là Chroma persistent với metric cosine. Chi phí API embedding là 0. Môi trường chạy là `D:\miniconda3\python.exe` (Python 3.13.2); đường dẫn model và cấu hình được ghi trong `results/ingestion_stats.json`. Kết quả có 248 chunk cho A và 275 chunk cho B/C.

## Cấu hình và benchmark

| Strategy | Chunking | Filter |
|---|---|---|
| A | Cửa sổ 500 ký tự, overlap 50 | Không |
| B | Gom theo đoạn/dòng, tối đa 500 ký tự | Không |
| C | Giống B, dùng cùng chunk và vector | Lọc `section` khi câu hỏi cung cấp phạm vi |

Bộ `benchmark/questions.json` có 20 câu: 15 dev và 5 test; 7 câu có metadata filter, trong đó có câu test. Gold evidence được ghi theo nguồn, trang và trích đoạn. Quy tắc chọn đã chốt trong `artifacts/experiment_plan.txt`: ưu tiên Evidence Hit@3 trên dev, nếu hòa thì Hit@1, rồi chọn B nếu vẫn hòa. Theo số liệu dev, C được chọn vì Hit@3 hòa với A/B và Hit@1 cao nhất. Test chỉ được dùng để báo cáo sau lựa chọn.

## Kết quả

### Truy xuất

| Strategy | Dev Hit@1 | Dev Evidence Hit@3 | Test Hit@1 | Test Evidence Hit@3 | Số chunk |
|---|---:|---:|---:|---:|---:|
| A | 4/15 | 8/15 | 2/5 | 2/5 | 248 |
| B | 5/15 | 8/15 | 3/5 | 3/5 | 275 |
| C | 6/15 | 8/15 | 3/5 | 3/5 | 275 |

Trace đầy đủ nằm ở `results/trace_dev.json` và `results/trace_test.json`; metric tổng hợp ở `results/metrics_dev.json` và `results/metrics_test.json`. Trên dev, C đứng đầu Hit@1 nhưng cả ba hòa Evidence Hit@3. Trên test nhỏ, B và C cùng đạt 3/5 ở cả hai metric; kết quả này chưa đủ để kết luận filter làm tăng chất lượng tổng thể.

Một lỗi dễ thấy là câu `q16` trong test của A: gold ở trang 3 của bài báo bổ sung, nhưng top-3 trả các trang 4, 6 và 11. Với `q20`, cả A/B/C không trả trang gold 13 trong top-3, dù vẫn có kết quả liên quan từ các trang khác. Các trường hợp này cho thấy top-3 có thể gần chủ đề nhưng không trúng đoạn bằng chứng đã chọn; cần xem trace cùng PDF trước khi diễn giải nguyên nhân.

### Chất lượng chunk, metadata và grounding

Các số bên dưới hiện là **nhãn audit do Codex hỗ trợ tạo, chưa được học viên kiểm tra độc lập**. Chúng chỉ nên được coi là số liệu sơ bộ cho đến khi tôi mở từng trace và đối chiếu PDF, sửa điểm/lý do nếu cần, rồi xác nhận bảng audit.

| Strategy | Coherence trung bình /2 (10 vị trí) | Metadata đúng/đủ | Filter tuân thủ | Grounding trung bình /2 (5 câu test) |
|---|---:|---:|---:|---:|
| A | 1.4 | 45/45 lượt hit được kiểm tra | N/A | 1.4 (0/1/2 = 1/1/3) |
| B | 1.5 | 45/45 lượt hit được kiểm tra | N/A | 1.8 (0/1/2 = 0/1/4) |
| C | 1.5 | 45/45 lượt hit được kiểm tra | 9/9 lượt có filter | 1.8 (0/1/2 = 0/1/4) |

Chi tiết điểm và lý do nằm trong `results/audit_coherence.json` và `results/audit_test.json`. Chỉ số metadata là kiểm tra các hit trong mẫu audit, không phải xác nhận toàn bộ collection. Grounding ở đây là mức top-3 cung cấp đủ bằng chứng, không đo tính đúng của câu trả lời do LLM sinh ra.

### Tác động, tài nguyên và giới hạn

A–B thay cách tạo chunk; B–C giữ chunk/vector như nhau và thay hành vi filter. B có Hit@1 cao hơn A 1 câu trên dev và test; C hơn B 1 câu Hit@1 trên dev nhưng không khác trên test. Coherence/grounding hiện chưa thể dùng làm kết luận cuối trước khi học viên xác nhận nhãn. Thời gian ingestion ghi trong `results/ingestion_stats.json` là 412.95 giây tổng; thời gian từng strategy trong file là A 180.93 giây, B 141.94 giây, C 1.02 giây. C dùng lại chunk/vector của B nên các thời gian này không phải phép đo độc lập ngang điều kiện. Chi phí embedding API bằng 0 vì embedding chạy local.

Giới hạn chính là chỉ có 20 câu và 5 câu test, phạm vi câu hỏi tập trung vào một số trang, corpus gồm hai bài cùng chủ đề, và một phần nhãn audit chưa được học viên kiểm chứng. Thời gian phụ thuộc máy và cache. Kết quả chỉ mô tả corpus và benchmark này, không đại diện mọi tài liệu. Nếu làm tiếp, tôi sẽ tự rà soát toàn bộ nhãn audit, bổ sung câu hỏi phủ đều các phần, rồi đo lại thời gian với cache được kiểm soát.

## Demo và cách chạy

Ứng dụng Flask gọi Mistral `ministral-8b-latest`; citation trả file, trang và bounding boxes để giao diện mở PDF đúng vị trí. Smoke test trước đó nhận HTTP 200 ở trang chính, status, trang PDF bổ sung và endpoint chat. Unit test: 5/5 passed. Không lưu API key trong Git; `starter/.env` phải được tạo từ mẫu cục bộ.

Các lệnh chạy lại pipeline, benchmark, lựa chọn strategy và unit test được ghi trong `starter/README.md` và bảng trạng thái ở `report/individual/TRANG_THAI.md`. Môi trường duy nhất của project là Miniconda base.

## Khai báo công cụ hỗ trợ

Codex được dùng để hỗ trợ sửa code, chạy kiểm tra kỹ thuật, tổng hợp metric và soạn bản nháp báo cáo/audit. Các metric truy xuất được lấy từ file kết quả đã chạy; riêng điểm coherence, grounding và kiểm tra metadata/filter hiện là bản nháp do công cụ hỗ trợ lập. Trước khi nộp, tôi cần tự xem lại nhãn audit theo `RULES.md`, xác nhận nội dung báo cáo, và ghi lại mọi chỉnh sửa. Tôi chỉ xác nhận những phần mình đã kiểm tra và có thể giải thích.
