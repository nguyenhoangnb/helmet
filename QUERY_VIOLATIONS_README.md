# Hướng dẫn chạy `app/query_violations.py`

File `app/query_violations.py` dùng để truy vấn dữ liệu vi phạm đã lưu trong SQLite database `app/violations.db`.

Script này chỉ đọc dữ liệu, không chỉnh sửa database.

## 1. Yêu cầu

- Chạy lệnh tại thư mục gốc project:

```bash
cd /home/hoang/yolo-helmet-detections
```

- Database mặc định phải tồn tại:

```text
app/violations.db
```

- Script dùng thư viện chuẩn Python, không cần cài thêm package ngoài.

## 2. Xem trợ giúp

```bash
python3 app/query_violations.py -h
```

Kết quả sẽ liệt kê các lệnh hỗ trợ:

```text
latest
missing-hash
stats
by-date
detail
search-hash
verify-image
```

## 3. Ví dụ thực tế trong project này

Các ví dụ dưới đây được chạy trực tiếp với database hiện tại:

```text
app/violations.db
```

Lưu ý: kết quả có thể thay đổi nếu bạn chạy app và phát sinh thêm vi phạm mới.

### 3.1. Kiểm tra tổng quan database

Lệnh:

```bash
python3 app/query_violations.py stats
```

Output mẫu trong project:

```text
total_violations | hashed_violations | missing_hash | local_chain_rows | real_blockchain_rows
-----------------+-------------------+--------------+------------------+---------------------
74               | 42                | 32           | 42               | 0
```

Ý nghĩa output này:

- Project đang có `74` bản ghi vi phạm.
- Có `42` bản ghi đã được tính `image_hash`.
- Có `32` bản ghi cũ chưa có `image_hash`.
- Có `42` bản ghi đang dùng `local-chain:...`.
- Chưa có transaction blockchain thật vì `real_blockchain_rows = 0`.

### 3.2. Xem 3 vi phạm mới nhất

Lệnh:

```bash
python3 app/query_violations.py latest --limit 3
```

Output mẫu:

```text
id | timestamp           | image_hash                                                       | blockchain_tx                | image_path
---+---------------------+------------------------------------------------------------------+------------------------------+--------------------------------------------------------------------------------
74 | 2026-05-30 20:17:11 | 655344358f6902fff9975ab81417d4e4e46941b270a0a5cba586eebdef40da54 | local-chain:655344358f6902ff | /home/hoang/yolo-helmet-detections/app/violations/violation_20260530_201711.jpg
73 | 2026-05-30 20:17:10 | 494c9623f2e1d701683d2bee9132d99b6162b0e3f1a3961b01e64cdd38eccc3a | local-chain:494c9623f2e1d701 | /home/hoang/yolo-helmet-detections/app/violations/violation_20260530_201710.jpg
72 | 2026-05-30 20:17:08 | f99dfadcbade11ceac99be0b335130a08e47a44365f2809c30b1bd5b408700be | local-chain:f99dfadcbade11ce | /home/hoang/yolo-helmet-detections/app/violations/violation_20260530_201708.jpg
```

Cách đọc:

- Bản ghi mới nhất là `id = 74`.
- Ảnh bằng chứng nằm ở `image_path`.
- `image_hash` là SHA-256 của ảnh đó.
- `blockchain_tx` đang là `local-chain:...`, nghĩa là chưa gửi blockchain thật.

### 3.3. Xem chi tiết một vi phạm cụ thể

Lấy `id` từ lệnh `latest`, ví dụ `74`, rồi chạy:

```bash
python3 app/query_violations.py detail 74
```

Output mẫu:

```text
id | timestamp           | camera         | violation_type        | image_path                                                                      | confidence         | image_hash                                                       | blockchain_tx                | ipfs_uri
---+---------------------+----------------+-----------------------+---------------------------------------------------------------------------------+--------------------+------------------------------------------------------------------+------------------------------+--------------------------------
74 | 2026-05-30 20:17:11 | Traffic Camera | Không đội mũ bảo hiểm | /home/hoang/yolo-helmet-detections/app/violations/violation_20260530_201711.jpg | 0.5125657916069031 | 655344358f6902fff9975ab81417d4e4e46941b270a0a5cba586eebdef40da54 | local-chain:655344358f6902ff | ipfs://pending/655344358f6902ff
```

Cách đọc:

- `camera`: nguồn phát hiện vi phạm.
- `violation_type`: loại vi phạm.
- `confidence`: độ tin cậy của model YOLO.
- `ipfs_uri`: hiện tại là placeholder, chưa phải IPFS thật.

### 3.4. Tìm bản ghi bằng một đoạn hash

Lệnh:

```bash
python3 app/query_violations.py search-hash 655344358f6902ff
```

Output mẫu:

```text
id | timestamp           | image_hash                                                       | blockchain_tx                | image_path
---+---------------------+------------------------------------------------------------------+------------------------------+--------------------------------------------------------------------------------
74 | 2026-05-30 20:17:11 | 655344358f6902fff9975ab81417d4e4e46941b270a0a5cba586eebdef40da54 | local-chain:655344358f6902ff | /home/hoang/yolo-helmet-detections/app/violations/violation_20260530_201711.jpg
```

Lệnh này hữu ích khi bạn chỉ có một đoạn `image_hash` hoặc `blockchain_tx` và muốn tìm lại ảnh bằng chứng.

### 3.5. Lấy ảnh bằng hash và kiểm tra ảnh có bị sửa không

Lệnh:

```bash
python3 app/query_violations.py verify-image 655344358f6902ff
```

Output mẫu:

```text
id | timestamp           | status | stored_hash                                                      | current_hash                                                     | image_path
---+---------------------+--------+------------------------------------------------------------------+------------------------------------------------------------------+--------------------------------------------------------------------------------
74 | 2026-05-30 20:17:11 | MATCH  | 655344358f6902fff9975ab81417d4e4e46941b270a0a5cba586eebdef40da54 | 655344358f6902fff9975ab81417d4e4e46941b270a0a5cba586eebdef40da54 | /home/hoang/yolo-helmet-detections/app/violations/violation_20260530_201711.jpg
```

Cách đọc:

- `stored_hash`: hash đang lưu trong database.
- `current_hash`: hash được tính lại từ file ảnh hiện tại.
- `status = MATCH`: ảnh hiện tại vẫn khớp với hash đã lưu, nghĩa là ảnh chưa bị thay đổi.

Nếu `status = MISMATCH`, ảnh hiện tại không còn khớp với hash trong database.

### 3.6. Thống kê vi phạm theo ngày

Lệnh:

```bash
python3 app/query_violations.py by-date
```

Output mẫu:

```text
violation_date | total
---------------+------
2026-05-30     | 28
2026-05-05     | 33
2026-05-02     | 13
```

Ví dụ này cho thấy ngày `2026-05-30` có `28` bản ghi vi phạm trong database.

### 3.7. Xem các bản ghi chưa có hash

Lệnh:

```bash
python3 app/query_violations.py missing-hash
```

Output mẫu rút gọn:

```text
id | timestamp           | image_path
---+---------------------+-----------------------------------------
45 | 2026-05-05 23:43:28 | violations/violation_20260505_234328.jpg
44 | 2026-05-05 23:43:21 | violations/violation_20260505_234320.jpg
43 | 2026-05-05 23:38:11 | violations/violation_20260505_233810.jpg
```

Các dòng này là dữ liệu cũ chưa có `image_hash`. Nếu muốn bổ sung hash cho những dòng này, chạy:

```bash
python3 app/backfill_violation_hashes.py
```

## 4. Xem các vi phạm mới nhất

Hiển thị 10 bản ghi mới nhất:

```bash
python3 app/query_violations.py latest
```

Giới hạn số lượng bản ghi:

```bash
python3 app/query_violations.py latest --limit 5
```

Các cột hiển thị:

- `id`: mã bản ghi vi phạm.
- `timestamp`: thời điểm phát hiện.
- `image_hash`: mã SHA-256 của ảnh bằng chứng.
- `blockchain_tx`: mã blockchain local hoặc transaction thật.
- `image_path`: đường dẫn ảnh bằng chứng.

## 5. Xem thống kê tổng quan

```bash
python3 app/query_violations.py stats
```

Ý nghĩa các cột:

- `total_violations`: tổng số bản ghi vi phạm.
- `hashed_violations`: số bản ghi đã có `image_hash`.
- `missing_hash`: số bản ghi chưa có `image_hash`.
- `local_chain_rows`: số bản ghi đang dùng mã `local-chain:...`.
- `real_blockchain_rows`: số bản ghi có transaction blockchain thật dạng `0x...`.

## 6. Xem bản ghi chưa có hash

```bash
python3 app/query_violations.py missing-hash
```

Lệnh này dùng để tìm các bản ghi cũ chưa được bổ sung `image_hash`.

Nếu muốn bổ sung hash cho dữ liệu cũ, chạy:

```bash
python3 app/backfill_violation_hashes.py
```

## 7. Thống kê số vi phạm theo ngày

```bash
python3 app/query_violations.py by-date
```

Kết quả gồm:

- `violation_date`: ngày phát hiện.
- `total`: số vi phạm trong ngày đó.

## 8. Xem chi tiết một bản ghi theo ID

Cú pháp:

```bash
python3 app/query_violations.py detail <id>
```

Ví dụ:

```bash
python3 app/query_violations.py detail 74
```

Lệnh này hiển thị đầy đủ các cột:

- `id`
- `timestamp`
- `camera`
- `violation_type`
- `image_path`
- `confidence`
- `image_hash`
- `blockchain_tx`
- `ipfs_uri`

## 9. Tìm theo hash hoặc transaction

Cú pháp:

```bash
python3 app/query_violations.py search-hash <text>
```

Ví dụ tìm theo một đoạn SHA-256:

```bash
python3 app/query_violations.py search-hash 655344358f6902ff
```

Ví dụ tìm các bản ghi local blockchain:

```bash
python3 app/query_violations.py search-hash local-chain
```

Ví dụ tìm transaction thật:

```bash
python3 app/query_violations.py search-hash 0x
```

## 10. Lấy ảnh bằng hash và so sánh SHA-256

Lệnh `verify-image` dùng để:

- Tìm bản ghi theo `image_hash` hoặc `blockchain_tx`.
- Lấy đường dẫn ảnh từ cột `image_path`.
- Tính lại SHA-256 của file ảnh hiện tại.
- So sánh hash tính lại với `image_hash` đang lưu trong database.

Cú pháp:

```bash
python3 app/query_violations.py verify-image <text>
```

Ví dụ kiểm tra bằng một đoạn SHA-256:

```bash
python3 app/query_violations.py verify-image 655344358f6902ff
```

Ví dụ kiểm tra bằng mã `local-chain`:

```bash
python3 app/query_violations.py verify-image local-chain:655344358f6902ff
```

Kết quả gồm:

- `id`: mã bản ghi vi phạm.
- `timestamp`: thời điểm phát hiện.
- `status`: trạng thái so sánh.
- `stored_hash`: hash đang lưu trong database.
- `current_hash`: hash tính lại từ file ảnh hiện tại.
- `image_path`: đường dẫn ảnh bằng chứng.

Ý nghĩa `status`:

- `MATCH`: ảnh hiện tại khớp với hash trong database, chứng cứ còn nguyên.
- `MISMATCH`: ảnh hiện tại không khớp hash trong database, có thể ảnh đã bị thay đổi hoặc không đúng file gốc.
- `MISSING_FILE`: database có đường dẫn ảnh nhưng file ảnh không còn tồn tại.
- `NO_STORED_HASH`: bản ghi chưa có `image_hash`, script chỉ tính hash hiện tại để tham khảo.

## 11. Dùng database khác

Mặc định script đọc:

```text
app/violations.db
```

Nếu muốn chỉ định database khác, dùng `--db`:

```bash
python3 app/query_violations.py --db /duong/dan/toi/violations.db stats
```

Ví dụ:

```bash
python3 app/query_violations.py --db app/violations.db latest --limit 3
```

Lệnh `verify-image` cũng dùng được với database khác:

```bash
python3 app/query_violations.py --db /duong/dan/toi/violations.db verify-image 655344358f6902ff
```

## 12. Lỗi thường gặp

### Database not found

Thông báo:

```text
FileNotFoundError: Database not found: app/violations.db
```

Nguyên nhân:

- Chưa chạy app để tạo database.
- Đang chạy lệnh sai thư mục.
- Truyền sai đường dẫn `--db`.

Cách xử lý:

```bash
cd /home/hoang/yolo-helmet-detections
python3 app/query_violations.py stats
```

### No rows found

Thông báo:

```text
No rows found.
```

Điều này không phải lỗi. Nghĩa là truy vấn không tìm thấy bản ghi phù hợp.

Ví dụ:

- Không có dòng thiếu hash.
- Không có hash hoặc transaction chứa đoạn text cần tìm.
- ID được truyền vào không tồn tại.

## 13. Gợi ý quy trình kiểm tra dữ liệu

Chạy lần lượt:

```bash
python3 app/query_violations.py stats
python3 app/query_violations.py latest --limit 5
python3 app/query_violations.py missing-hash
python3 app/query_violations.py by-date
```

Nếu muốn kiểm tra một bản ghi cụ thể, lấy `id` từ lệnh `latest`, rồi chạy:

```bash
python3 app/query_violations.py detail <id>
```

Nếu muốn kiểm tra ảnh bằng chứng có còn khớp hash không, lấy một đoạn `image_hash` hoặc `blockchain_tx` từ lệnh `latest`, rồi chạy:

```bash
python3 app/query_violations.py verify-image <hash_or_tx>
```
