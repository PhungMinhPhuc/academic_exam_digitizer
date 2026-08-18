# Local hybrid RAG

Pipeline tìm kiếm SGK bằng `pgvector` + BM25s, hợp nhất kết quả bằng RRF và
trả về bài học tương ứng trong `curriculum.py`.

Các lệnh dưới đây chạy từ thư mục `ai-engine/`.

## 1. Cài đặt và khởi động PostgreSQL

```powershell
..\.venv\Scripts\python.exe -m pip install sentence-transformers "psycopg[binary]" pgvector bm25s modal
docker compose -f rag\docker-compose.yml up -d
$env:RAG_DATABASE_URL = "postgresql://exam_rag:rag_local@localhost:5432/exam_rag"
```

## 2. Tạo index

Nguồn mặc định là toàn bộ `data/subject_embed/*.json`.

```powershell
# Vector: xóa section cũ theo từng book_id rồi ingest lại
..\.venv\Scripts\python.exe -m rag.vectorize

# BM25s: rebuild toàn bộ corpus
..\.venv\Scripts\python.exe -m rag.build_bm25s
```

Chạy riêng một sách:

```powershell
# Vector: append mặc định; dùng replace để xóa section cũ của sách trước
..\.venv\Scripts\python.exe -m rag.vectorize `
  --source ..\data\subject_embed\math10_embed.json `
  --mode replace

# BM25s: chọn append cho nguồn mới hoặc overwrite cho nguồn đã có
..\.venv\Scripts\python.exe -m rag.build_bm25s `
  --source ..\data\subject_embed\math10_embed.json `
  --mode overwrite
```

Mỗi JSON phải có `book_id` ở cấp cao nhất. Model mặc định là
`AITeamVN/Vietnamese_Embedding`, đầu ra 1024 chiều.

## 3. Tìm kiếm

```powershell
..\.venv\Scripts\python.exe -m rag.search `
  --original-query `
  --no-formula-rewrite `
  --no-method-rewrite `
  --no-rerank
```

Dán câu hỏi vào terminal và nhập một dòng trống để chạy. Lệnh trên chỉ truy hồi
bằng câu hỏi gốc và không gọi Modal.

Deploy các worker rewrite và rerank lên hai Modal app:

```powershell
..\.venv\Scripts\modal.exe deploy rag\rewrite_modal.py
..\.venv\Scripts\modal.exe deploy rag\rerank_modal.py
```

Formula/method rewrite mặc định dùng `qwen3-14b-awq`. Chọn Qwen3-4B bằng:

```powershell
..\.venv\Scripts\python.exe -m rag.search --formula-rewrite-model qwen3-4b
```

`formula rewrite` chỉ mô tả từng công thức và không suy diễn. `method rewrite`
đọc toàn câu hỏi và sinh đúng một truy vấn về kiến thức/phép biến đổi cần dùng,
không giải bài. Hai nhiệm vụ dùng prompt, schema và fallback độc lập.

Ba query view được điều khiển riêng:

```text
--original-query / --no-original-query
--formula-rewrite / --no-formula-rewrite
--method-rewrite / --no-method-rewrite
```

Mặc định bật original + formula và tắt method. Chạy method-only bằng:

```powershell
..\.venv\Scripts\python.exe -m rag.search `
  --no-original-query `
  --no-formula-rewrite `
  --method-rewrite
```

Ít nhất một view phải được bật. Nếu method-only nhưng worker không tạo được
`method_query` hợp lệ, lệnh báo lỗi thay vì âm thầm dùng original.

Rerank mặc định dùng `qwen3-reranker-4b`. Có thể chọn bản nhẹ hơn bằng
`--rerank-model qwen3-reranker-0.6b`; `--rerank-class-name` cho phép trỏ tới một
Modal class khác có cùng contract mà không sửa luồng search. Dùng `--no-rerank`
để giữ nguyên thứ tự RRF khi benchmark hoặc khi worker chưa deploy.

```powershell
..\.venv\Scripts\python.exe -m rag.search `
  --rerank-model qwen3-reranker-0.6b
```

Các bộ lọc đều tùy chọn:

```powershell
..\.venv\Scripts\python.exe -m rag.search `
  --original-query `
  --no-formula-rewrite `
  --no-method-rewrite `
  --no-rerank `
  --subject Toán `
  --grade 10 `
  --book-id toan10_kntt `
  --debug
```

Mỗi query view chạy vector + BM25 riêng. Tất cả ranking được hợp nhất bằng RRF
với `rrf_k=20`; query trùng được loại trước retrieval. Chỉ tối đa 10 kết quả RRF
đầu được rerank bằng `original_query` trước khi cắt `top_k`.
Không có `--debug`, output chỉ gồm:

```json
{
  "Grade": 10,
  "Chapter": "Hàm số, đồ thị và ứng dụng",
  "Lesson": "Hàm số bậc hai",
  "Complexity": null
}
```

`--debug` trả thêm `formula_query`, `method_query`, `query_views`, số kết quả theo
từng retrieval run, rank/score theo từng view, RRF, rerank và thời gian xử lí.
Tiêu đề chương, bài lấy từ `curriculum.DATA`; nếu không ánh xạ được thì bốn
trường phân loại đều là `null`.

## 4. Phân loại nhiều câu hỏi

Đọc đề từ file và ghi kết quả cạnh file đầu vào. Ví dụ sau tạo
`test/result_math1.json`:

```powershell
..\.venv\Scripts\python.exe -m rag.batch_search `
  --input ..\test\math1.txt `
  --output ..\test\result_math1.json `
  --formula-rewrite-model qwen3-4b `
  --method-rewrite
```

Bỏ `--input` để dán đề trực tiếp vào terminal; nhập một dòng chỉ chứa `END` để
kết thúc. Dùng `--output` để chọn file đích. Tiến độ tách đề, nạp model/index và
phân loại từng query được in trên console. Các câu có phần `a)`, `b)`, ... được
tách thành đề chung cộng với từng phần tương ứng. `Complexity` mặc định là
`null` để dành cho model đánh giá sau này.

Để lưu riêng 10 candidates sau rerank của mỗi câu mà không đổi schema file kết
quả chính:

```powershell
..\.venv\Scripts\python.exe -m rag.batch_search `
  --input ..\test\math1.txt `
  --output ..\test\result_math1.json `
  --debug-output ..\test\result_math1_debug.json `
  --debug-candidates 10 `
  --subject Toán
```

Mỗi query trong file debug có classification cuối, các query view, timing và
mảng `candidates`. Mỗi candidate kèm provenance vector/BM25 theo original,
formula hoặc method, điểm RRF và rerank.

Khi formula hoặc method rewrite cùng rerank được bật, batch mặc định dùng
`--modal-warmup`: gửi hai
warmup call bằng `spawn()` trước rồi mới chờ kết quả, nên hai container nạp model
đồng thời. Query đầu tiên chỉ chạy sau khi cả hai worker báo `ready`. Dùng
`--no-modal-warmup` để quay lại khởi động tuần tự theo nhu cầu.

Khi formula hoặc method rewrite được bật, batch mặc định stream stdout của Modal
worker về cùng terminal (`--formula-rewrite-modal-logs`). Dùng
`--no-formula-rewrite-modal-logs` nếu chỉ muốn log tiến độ local. Rerank có cặp
flag tương ứng `--rerank-modal-logs` và
`--no-rerank-modal-logs`. Có thể theo dõi độc lập log trong terminal khác:

```powershell
..\.venv\Scripts\modal.exe app logs exam-rag-qwen3-rewrite -f --timestamps
..\.venv\Scripts\modal.exe app logs exam-rag-qwen3-rerank -f --timestamps
```

Worker ghi các mốc nạp model, nhận request, bắt đầu/kết thúc generate, fallback
và thời gian; không ghi nguyên văn câu hỏi.

## 5. Xóa database local

Lệnh sau xóa toàn bộ dữ liệu PostgreSQL local:

```powershell
docker compose -f rag\docker-compose.yml down -v
```
