# YOLO Helmet Detection

Ứng dụng Streamlit nhận diện người không đội mũ bảo hiểm bằng YOLO, lưu ảnh bằng chứng, tạo SHA-256 hash và lưu dữ liệu vi phạm vào SQLite.

Project đang hỗ trợ 2 chế độ:

- Local: lưu hash vào SQLite và tạo mã `local-chain:...`
- Blockchain thật: gửi hash lên smart contract nếu đã cấu hình Web3

## 1. Kích hoạt môi trường

Project dùng Conda env:

```bash
conda activate robot_env
```

Cài dependency:

```bash
pip install -r requirements.txt
```

## 2. Chạy app Streamlit

Chạy từ thư mục gốc project:

```bash
streamlit run app/main.py
```

Mở trình duyệt:

```text
http://localhost:8501
```

Trong app, chọn:

- `Hình ảnh`: upload ảnh để nhận diện
- `Video`: upload video để xử lý

Khi phát hiện vi phạm, app sẽ lưu:

- Ảnh bằng chứng: `app/violations/`
- Database: `app/violations.db`
- SHA-256 hash: cột `image_hash`
- Mã local blockchain: cột `blockchain_tx`

## 3. Chế độ local blockchain

Nếu bạn chỉ chạy local, không cần tạo ví, không cần MetaMask, không cần deploy contract.

Không cần cấu hình các biến này:

```env
BLOCKCHAIN_RPC_URL=
BLOCKCHAIN_PRIVATE_KEY=
BLOCKCHAIN_CONTRACT_ADDRESS=
```

Khi đó cột `blockchain_tx` sẽ có dạng:

```text
local-chain:51884e69c78a2185
```

Đây là mã mô phỏng local, lấy 16 ký tự đầu của SHA-256 hash.

## 4. Cấu hình Telegram

Tạo file:

```text
app/.env
```

Thêm:

```env
TELEGRAM_TOKEN=token_cua_ban
TELEGRAM_CHAT_ID=chat_id_cua_ban
```

Nếu không cấu hình Telegram, app vẫn chạy nhưng không gửi cảnh báo.

## 5. Backfill hash cho dữ liệu cũ

Một số dòng cũ trong database có thể chưa có `image_hash` và `blockchain_tx`.

Chạy:

```bash
python app/backfill_violation_hashes.py
```

Script sẽ:

- Tìm dòng chưa có hash
- Đọc ảnh từ `image_path`
- Tính SHA-256
- Ghi `image_hash`
- Ghi `blockchain_tx` dạng `local-chain:...`
- Ghi `ipfs_uri` dạng `ipfs://pending/...`

Ví dụ output:

```text
Updated rows: 14
Missing images: 32
```

Trong đó:

- `Updated rows`: số dòng cập nhật thành công
- `Missing images`: số dòng không cập nhật được vì ảnh không còn tồn tại

## 6. Truy vấn database bằng Python

File truy vấn:

```text
app/query_violations.py
```

Xem thống kê tổng quan:

```bash
python app/query_violations.py stats
```

Xem 10 vi phạm mới nhất:

```bash
python app/query_violations.py latest
```

Xem 5 vi phạm mới nhất:

```bash
python app/query_violations.py latest --limit 5
```

Xem các dòng chưa có hash:

```bash
python app/query_violations.py missing-hash
```

Đếm vi phạm theo ngày:

```bash
python app/query_violations.py by-date
```

Xem chi tiết một bản ghi theo ID:

```bash
python app/query_violations.py detail 1
```

Tìm theo hash hoặc mã `local-chain`:

```bash
python app/query_violations.py search-hash 51884e69
```

## 7. Truy vấn database bằng sqlite3

Mở database:

```bash
sqlite3 app/violations.db
```

Xem 10 dòng mới nhất:

```sql
SELECT id, timestamp, image_hash, blockchain_tx, image_path
FROM violations
ORDER BY id DESC
LIMIT 10;
```

Xem dòng chưa có hash:

```sql
SELECT id, timestamp, image_path
FROM violations
WHERE image_hash IS NULL OR image_hash = ''
ORDER BY id DESC;
```

Thoát SQLite:

```sql
.exit
```

Xem thêm hướng dẫn SQL tại:

```text
SQL_TEST_README.md
```

## 8. Blockchain thật

Nếu muốn gửi hash lên blockchain thật, xem:

```text
BLOCKCHAIN.md
```

File smart contract:

```text
contracts/ViolationRegistry.sol
```

Khi blockchain thật chạy đúng, cột `blockchain_tx` sẽ có dạng:

```text
0x...
```

Nếu chỉ build local, bạn không cần phần này.

## 9. Các lệnh cũ trong project

Chạy file xử lý khác:

```bash
streamlit run app/processing.py
```

Chạy server:

```bash
cd app
python3 server.py
```

Chạy stream video:

```bash
cd app
python3 stream_video.py
```

Chạy stream camera:

```bash
cd app
python3 stream_cam.py
```

Ghi chú: có thể đổi model trong hàm `load_model()` của `app/main.py` để test các file weight khác.
