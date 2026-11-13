# Rà soát file nộp Day 6

## Nội dung cần đưa vào repo nộp

| Hạng mục | File hiện có | Tình trạng |
|---|---|---|
| Thông tin học viên | `STUDENT.md` | Đã điền tên/MSSV/lớp theo tên workspace; cần xác nhận cách viết họ tên và điền link repo cùng commit chốt. |
| Hướng dẫn và code chạy | `README.md`, `starter/README.md`, `starter/src/` | Có. Kiểm tra lại hướng dẫn chạy từ repo sạch trước khi nộp. |
| Manifest corpus | `data/corpus_manifest.json`, `data/manifest.json` | Có nguồn, version, số trang, quyền và SHA-256. `data/data.pdf` hiện bị ignore; cần bảo đảm người chấm tải được đúng bản theo hướng dẫn. |
| Benchmark | `benchmark/questions.json`, `BENCHMARK.md` | Có 20 câu (15 dev/5 test), câu hỏi filter và gold evidence. |
| Kế hoạch và log | `artifacts/experiment_plan.txt`, `artifacts/experiment_log.csv` | Đã điền cấu hình/kết quả. Câu giả thuyết trong log được diễn đạt lại từ kế hoạch và cấu hình hiện có; cần học viên xác nhận, không coi là bản ghi có timestamp trước khi chạy. |
| Kết quả retrieval | `results/metrics_*.json`, `results/trace_*.json` | Có metric và trace dev/test cho A/B/C. |
| Audit thủ công | `results/audit_coherence.json`, `results/audit_test.json` | Có bản nháp điểm/lý do do Codex hỗ trợ tạo; học viên phải tự đối chiếu và xác nhận trước khi nộp để đáp ứng yêu cầu audit thủ công. |
| Báo cáo đúng tên | `report/individual/2A202603648_GiapManhTuyen.md` | Đã tạo; cần đọc lại, xác nhận phần thông tin cá nhân, nhãn audit và có thể giải thích các quyết định. |
| Báo cáo trạng thái | `report/individual/TRANG_THAI.md` | Có bảng đối chiếu kỹ thuật. Đọc cùng báo cáo cá nhân; audit trong đó cũng chưa được học viên xác nhận. |

## Trước khi push

- [ ] Xác nhận tên có dấu, lớp và mã số trong `STUDENT.md`.
- [ ] Điền repo cá nhân và commit chốt trong `STUDENT.md`; kiểm tra repo mở được cho giảng viên/coach.
- [ ] Tự kiểm tra nhãn coherence, grounding, metadata và filter trong hai file audit; cập nhật báo cáo theo điểm đã xác nhận.
- [ ] Đọc lại giả thuyết trong experiment log và sửa để phản ánh đúng điều đã dự kiến. Kế hoạch hiện có ghi tiêu chí chọn trước test, nhưng không lưu timestamp riêng cho log giả thuyết.
- [ ] Đảm bảo `starter/.env`, API key, `data/data.pdf` nếu chưa rõ quyền tái phân phối, cache Chroma, môi trường và file tạm không bị commit. `data/data.pdf` bị ignore; cung cấp link tải/đối chiếu hash cho người chấm.
- [ ] Kiểm tra `git status` và `git diff --check`, sau đó push và nộp URL theo kênh/lịch của lớp.

## Không đưa lên repo

Không commit `starter/.env` hoặc bất kỳ API key/token nào. Không đưa PDF chính `data/data.pdf` lên repo khi quyền tái phân phối chưa được xác minh. File đang được ignore cần kiểm tra bằng `git status --ignored` để biết chính xác những gì sẽ không xuất hiện cho người chấm. Giữ `data/quantum-oscillator.pdf` cùng attribution/source link theo CC BY 4.0.

## AI và kiểm tra

Quy tắc `RULES.md` yêu cầu khai báo công cụ AI và cách kiểm tra. Báo cáo cá nhân có phần khai báo: Codex hỗ trợ code, tổng hợp và bản nháp audit; unit test/smoke test/metric được ghi theo kết quả chạy, còn nhãn audit phải được học viên tự xác nhận. Không nên xoá phần khai báo hoặc mô tả công cụ tạo nhãn như thể học viên tự chấm.
