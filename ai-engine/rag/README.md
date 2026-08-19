# Local hybrid RAG

Pipeline tìm kiếm SGK bằng `pgvector` + BM25s, hợp nhất kết quả bằng RRF và
trả về bài học tương ứng trong `curriculum.py`.

Các lệnh dưới đây chạy từ thư mục `ai-engine/`.

## 1. Cài đặt và khởi động PostgreSQL

```powershell
python -m pip install -r rag\requirements.txt
docker compose -f rag\docker-compose.yml up -d
$env:RAG_DATABASE_URL = "postgresql://exam_rag:rag_local@localhost:5432/exam_rag"
```

## Luồng chạy

```text
data/subject_embed/*.json
  ├─ rag.vectorize     → embedding → PostgreSQL/pgvector
  └─ rag.build_bm25s   → index → rag/artifacts/bm25s

1 câu hỏi  → rag.search       → HybridSearcher → curriculum.py → kết quả bài học
Cả đề      → rag.batch_search → tách câu hỏi   → HybridSearcher từng câu → JSON
```

Chạy lại `vectorize` và `build_bm25s` sau khi thay đổi dữ liệu
`data/subject_embed/`. `batch_search` dùng lại `HybridSearcher` của `search`,
không tạo index riêng.

## 2. Tạo index

Nguồn mặc định là toàn bộ `data/subject_embed/*.json`.

```powershell
# Vector: xóa section cũ theo từng book_id rồi ingest lại
python -m rag.vectorize

# BM25s: rebuild toàn bộ corpus
python -m rag.build_bm25s
```

Chạy riêng một sách:

```powershell
# Vector: append mặc định; dùng overwrite để xóa section cũ của sách trước
python -m rag.vectorize `
  --source ..\data\subject_embed\math10_embed.json `
  --mode overwrite

# BM25s: chọn append cho nguồn mới hoặc overwrite cho nguồn đã có
python -m rag.build_bm25s `
  --source ..\data\subject_embed\math10_embed.json `
  --mode overwrite
```

Mỗi JSON phải có `book_id` ở cấp cao nhất. Model mặc định là
`AITeamVN/Vietnamese_Embedding`, đầu ra 1024 chiều.

## 3. Tìm kiếm

### Tìm kiếm 1 câu hỏi

Tìm kiếm bằng text gốc:

```powershell
python -m rag.search `
  --original-query `
  --no-formula-rewrite `
  --no-method-rewrite `
  --no-rerank
```

Dán câu hỏi vào terminal và nhập một dòng trống để chạy.

Deploy các worker rewrite và rerank lên hai Modal app:

```powershell
python -m modal deploy rag\rewrite_modal.py
python -m modal deploy rag\rerank_modal.py
```

Formula/method rewrite dùng `qwen3-4b`.

`formula rewrite` chỉ mô tả từng công thức và không suy diễn. `method rewrite`
đọc toàn câu hỏi, sinh method query cùng dữ kiện liên quan, mục tiêu, hướng biến
đổi và phương pháp cần dùng; không giải bài hoặc sinh nhãn curriculum. Hai nhiệm
vụ dùng prompt, schema và fallback độc lập.

Ba query view được điều khiển riêng:

```text
--original-query / --no-original-query
--formula-rewrite / --no-formula-rewrite
--method-rewrite / --no-method-rewrite
```

Mặc định bật original + formula và tắt method.

```powershell
python -m rag.search `
  --no-original-query `
  --no-formula-rewrite `
  --method-rewrite
```

Có thể bật nhiều dạng query cùng lúc, các kết quả sẽ được kết hợp bằng RRF. Ít nhất một view phải được bật. 

Rerank mặc định dùng `qwen3-reranker-4b`. Có thể chọn bản nhẹ hơn bằng
`--rerank-model qwen3-reranker-0.6b`;. 

Mặc định reranker vẫn dùng `original_query`. Chạy lệnh sau để thử `structured rerank query` được
tạo bằng LLM:

```powershell
python -m rag.search `
  --method-rewrite `
  --rerank-query-mode structured `
  --rerank-method-min-confidence 0.7 `
  --debug
```

Các flag tùy chọn:

```powershell
python -m rag.search `
  --original-query `
  --no-formula-rewrite `
  --no-method-rewrite `
  --no-rerank `
  --subject Toán `
  --grade 10 `
  --book-id toan10_kntt `
  --debug
```

Không có `--debug`, output chỉ gồm:

```json
{
  "Grade": 10,
  "Chapter": "Chương 1. Hàm số, đồ thị và ứng dụng",
  "Lesson": "Bài 1. Hàm số bậc hai",
  "Complexity": null
}
```

`--debug` trả thêm `formula_query`, `method_query`, `method_analysis`, query focus,
rerank query/mode/fallback, `query_views`, số kết quả theo từng retrieval run,
rank/score theo từng view, RRF, rerank và thời gian xử lí.
Tiêu đề chương, bài (bao gồm tiền tố `Chương N.` và `Bài N.`) lấy từ
`curriculum.DATA`; nếu không ánh xạ được thì bốn trường phân loại đều là `null`.

## 4. Phân loại nhiều câu hỏi

Đọc đề từ file và ghi kết quả cạnh file đầu vào. Ví dụ sau tạo
`test/result_math1.json`:

```powershell
python -m rag.batch_search `
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

Có thể lưu riêng candidates để debug của mỗi câu:

```powershell
python -m rag.batch_search `
  --input ..\test\math1.txt `
  --output ..\test\result_math1.json `
  --debug-output ..\test\result_math1_debug.json `
  --debug-candidates 10 `
  --subject Toán
```

Khi formula hoặc method rewrite cùng rerank được bật, xử lý theo giai đoạn:
rewrite toàn bộ query, giải phóng model rewrite, rồi nạp reranker và xử lí toàn bộ
candidates.
