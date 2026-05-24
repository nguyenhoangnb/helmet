# Test dữ liệu vi phạm bằng SQLite

File này dùng để kiểm tra dữ liệu vi phạm trong chế độ local.

Trong chế độ local, app không ghi lên blockchain thật. App sẽ lưu:

- Ảnh bằng chứng trong `app/violations/`
- Dữ liệu vi phạm trong `app/violations.db`
- SHA-256 của ảnh trong cột `image_hash`
- Mã giả lập blockchain trong cột `blockchain_tx`, dạng `local-chain:...`

## 1. Mở database

Chạy từ thư mục gốc project:

```bash
sqlite3 app/violations.db
```

Nếu vào được SQLite, bạn sẽ thấy:

```text
sqlite>
```

## 2. Xem cấu trúc bảng

```sql
.schema violations
```

Bảng cần có các cột chính:

```text
id
timestamp
camera
violation_type
image_path
confidence
image_hash
blockchain_tx
ipfs_uri
```

## 3. Xem 10 vi phạm mới nhất

```sql
SELECT id, timestamp, image_hash, blockchain_tx, image_path
FROM violations
ORDER BY id DESC
LIMIT 10;
```

Kết quả local hợp lệ sẽ giống:

```text
46|2026-05-05 23:53:46|7b0b17e3...|local-chain:7b0b17e3dbeb7168|violations/violation_20260505_235346.jpg
```

## 4. Kiểm tra dòng nào chưa có hash

```sql
SELECT id, timestamp, image_path
FROM violations
WHERE image_hash IS NULL OR image_hash = ''
ORDER BY id DESC;
```

Nếu có kết quả, nghĩa là các dòng đó chưa được tính SHA-256.

Nguyên nhân thường gặp:

- Dữ liệu được tạo trước khi app có chức năng hash.
- File ảnh trong `image_path` đã bị xóa hoặc không còn tồn tại.

## 5. Backfill hash cho dữ liệu cũ

Chạy:

```bash
conda activate robot_env
python app/backfill_violation_hashes.py
```

Script sẽ:

- Tìm các dòng chưa có `image_hash`
- Đọc ảnh từ `image_path`
- Tính SHA-256
- Cập nhật `image_hash`
- Cập nhật `blockchain_tx` dạng `local-chain:...`
- Cập nhật `ipfs_uri` dạng `ipfs://pending/...`

Ví dụ output:

```text
Updated rows: 14
Missing images: 32
```

Trong đó:

- `Updated rows`: số dòng đã cập nhật được.
- `Missing images`: số dòng không cập nhật được vì không tìm thấy ảnh.

## 6. Kiểm tra lại sau backfill

```sql
SELECT id, timestamp, substr(image_hash, 1, 16) AS hash_prefix, blockchain_tx, image_path
FROM violations
ORDER BY id DESC
LIMIT 20;
```

Nếu thấy:

```text
local-chain:...
```

thì local blockchain đã được mô phỏng đúng.

## 7. Đếm tổng số vi phạm

```sql
SELECT COUNT(*) AS total_violations
FROM violations;
```

## 8. Đếm số dòng đã có hash

```sql
SELECT COUNT(*) AS hashed_violations
FROM violations
WHERE image_hash IS NOT NULL AND image_hash != '';
```

## 9. Đếm số dòng chưa có hash

```sql
SELECT COUNT(*) AS missing_hash
FROM violations
WHERE image_hash IS NULL OR image_hash = '';
```

## 10. Xem dữ liệu theo ngày

```sql
SELECT DATE(timestamp) AS violation_date, COUNT(*) AS total
FROM violations
GROUP BY DATE(timestamp)
ORDER BY violation_date DESC;
```

## 11. Xem các vi phạm có độ tin cậy cao

```sql
SELECT id, timestamp, confidence, image_hash, blockchain_tx
FROM violations
WHERE confidence >= 0.5
ORDER BY confidence DESC;
```

## 12. Kiểm tra một ảnh cụ thể

Ví dụ kiểm tra bản ghi có `id = 1`:

```sql
SELECT id, timestamp, image_path, image_hash, blockchain_tx, ipfs_uri
FROM violations
WHERE id = 1;
```

## 13. Thoát SQLite

```sql
.exit
```

## 14. Ý nghĩa local-chain

Ví dụ:

```text
image_hash:
51884e69c78a218557efda063f0869690edec6c48bf11e8739098c1044b0295b

blockchain_tx:
local-chain:51884e69c78a2185
```

Trong chế độ local:

- `image_hash` là SHA-256 thật của ảnh.
- `blockchain_tx` không phải transaction thật.
- `local-chain:51884e69c78a2185` là mã mô phỏng, lấy 16 ký tự đầu của hash.

Nếu dùng blockchain thật, `blockchain_tx` sẽ có dạng:

```text
0x...
```
