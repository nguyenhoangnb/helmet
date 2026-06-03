# Tài liệu web Streamlit nhận diện vi phạm mũ bảo hiểm

Tài liệu này mô tả cách web Streamlit trong thư mục `app/` hoạt động, cấu trúc giao diện, luồng xử lý dữ liệu và vai trò của các hàm chính.

## 1. Tổng quan

Web Streamlit dùng mô hình YOLO để phát hiện người không đội mũ bảo hiểm từ ảnh hoặc video. Khi phát hiện vi phạm, hệ thống sẽ:

1. Vẽ bounding box lên ảnh hoặc frame video.
2. Lưu ảnh bằng chứng vào `app/violations/`.
3. Tính mã băm SHA-256 của ảnh bằng chứng.
4. Tạo IPFS URI tạm thời.
5. Ghi hash lên Blockchain thật nếu đã cấu hình Web3, hoặc tạo mã local dạng `local-chain:...`.
6. Lưu toàn bộ thông tin vi phạm vào SQLite tại `app/violations.db`.
7. Gửi cảnh báo Telegram nếu đã cấu hình `TELEGRAM_TOKEN` và `TELEGRAM_CHAT_ID`.

Chạy app:

```bash
conda activate robot_env
streamlit run app/main.py
```

URL mặc định:

```text
http://localhost:8501
```

## 2. Cấu trúc thư mục web

```text
app/
├── main.py
├── violation_ui.py
├── query_violations.py
├── backfill_violation_hashes.py
├── violations.db
├── violations/
│   └── violation_*.jpg
├── uploads/
│   └── *.jpg
├── pages/
│   ├── 1_Dashboard.py
│   ├── 2_Danh_sach_vi_pham.py
│   ├── 3_Xac_thuc_SHA256.py
│   └── 4_Thong_ke.py
└── .streamlit/
    └── config.toml
```

Ý nghĩa chính:

| File hoặc thư mục | Vai trò |
| --- | --- |
| `main.py` | Trang chính của web. Chạy YOLO, xử lý ảnh/video, lưu vi phạm, hiển thị dashboard tổng quan. |
| `violation_ui.py` | Module dùng chung cho các trang dashboard, danh sách, xác thực và thống kê. |
| `pages/` | Các trang phụ của Streamlit multipage app. |
| `query_violations.py` | Công cụ dòng lệnh để truy vấn, tìm kiếm, xác thực dữ liệu vi phạm. |
| `backfill_violation_hashes.py` | Script bổ sung SHA-256 và Blockchain TX local cho dữ liệu cũ. |
| `violations.db` | SQLite database lưu các bản ghi vi phạm. |
| `violations/` | Nơi lưu ảnh bằng chứng khi phát hiện vi phạm. |
| `uploads/` | Nơi chứa một số ảnh upload hoặc ảnh mẫu. |

## 3. Cấu trúc giao diện

App có một sidebar điều hướng tùy chỉnh:

```text
🏠 Dashboard
📋 Danh sách vi phạm
🔒 Xác thực SHA-256
📊 Thống kê
```

### 3.1. Trang chính `main.py`

Trang chính gồm các phần:

| Khu vực | Chức năng |
| --- | --- |
| Hero | Giới thiệu hệ thống nhận diện không đội mũ bảo hiểm. |
| Thanh trạng thái | Hiển thị model, confidence threshold, IoU threshold, trạng thái Telegram và Blockchain. |
| Dashboard thống kê vi phạm | Tổng số vi phạm, đã băm SHA-256, chưa băm, giao dịch Blockchain, vi phạm trong ngày. |
| Danh sách gần nhất | Bảng các vi phạm mới nhất từ SQLite. |
| Thống kê theo ngày | Biểu đồ cột theo ngày. |
| Tìm theo hash | Tìm bản ghi bằng SHA-256 hoặc Blockchain TX. |
| Nguồn dữ liệu | Tab upload ảnh và upload video. |
| Lịch sử thống kê | Bảng thống kê tạm trong session, có nút tải CSV. |

### 3.2. Trang `pages/1_Dashboard.py`

Trang này gọi hàm `render_dashboard()` trong `violation_ui.py`. Nó dùng lại cùng logic thống kê với dashboard chính:

- Tổng số vi phạm.
- Số bản ghi đã băm SHA-256.
- Số bản ghi chưa băm SHA-256.
- Số giao dịch Blockchain.
- Số vi phạm trong ngày.
- Bảng vi phạm gần nhất.
- Biểu đồ thống kê theo ngày.

### 3.3. Trang `pages/2_Danh_sach_vi_pham.py`

Trang này hiển thị:

- Bảng toàn bộ bản ghi vi phạm.
- Chọn ID để xem chi tiết.
- Ảnh bằng chứng.
- Thời gian.
- Loại vi phạm.
- Độ tin cậy YOLO.
- SHA-256.
- Blockchain TX.
- IPFS URI.
- Nút tính lại SHA-256 ảnh đang chọn.
- Ô tìm kiếm theo hash.

### 3.4. Trang `pages/3_Xac_thuc_SHA256.py`

Trang này thay thế thao tác dòng lệnh:

```bash
python app/query_violations.py verify-image <hash>
```

Bằng giao diện:

1. Nhập SHA-256 hoặc một phần Blockchain TX.
2. Bấm `Kiểm tra`.
3. App tìm bản ghi trong SQLite.
4. App đọc lại file ảnh thật.
5. App tính SHA-256 hiện tại của file.
6. So sánh với hash lưu trong database.

Kết quả:

```text
MATCH
```

hoặc:

```text
MISMATCH
```

### 3.5. Trang `pages/4_Thong_ke.py`

Trang này hiển thị:

- Tổng số vi phạm.
- Đã băm SHA-256.
- Chưa băm SHA-256.
- Giao dịch Blockchain.
- Biểu đồ số vi phạm theo ngày.
- Bảng thống kê theo ngày.

## 4. Database SQLite

Database nằm tại:

```text
app/violations.db
```

Bảng chính:

```sql
CREATE TABLE violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    camera TEXT,
    violation_type TEXT,
    image_path TEXT,
    confidence REAL,
    image_hash TEXT,
    blockchain_tx TEXT,
    ipfs_uri TEXT
);
```

Ý nghĩa các cột:

| Cột | Ý nghĩa |
| --- | --- |
| `id` | ID tự tăng của bản ghi vi phạm. |
| `timestamp` | Thời điểm phát hiện vi phạm. |
| `camera` | Tên camera hoặc nguồn dữ liệu. |
| `violation_type` | Loại vi phạm, ví dụ `Không đội mũ bảo hiểm`. |
| `image_path` | Đường dẫn ảnh bằng chứng. |
| `confidence` | Độ tin cậy YOLO của vi phạm tốt nhất trong frame. |
| `image_hash` | SHA-256 của ảnh bằng chứng. |
| `blockchain_tx` | Transaction hash thật hoặc mã local `local-chain:...`. |
| `ipfs_uri` | URI IPFS tạm thời hoặc CID thật nếu sau này tích hợp upload IPFS. |

## 5. Luồng hoạt động khi xử lý ảnh

Khi người dùng upload ảnh:

1. Streamlit đọc ảnh bằng `PIL.Image`.
2. Ảnh được chuyển sang `numpy.ndarray`.
3. `process_image()` gọi model YOLO.
4. YOLO trả về danh sách bounding box.
5. `draw_boxes()` duyệt qua từng box:
   - Đọc class ID.
   - Đọc confidence.
   - Xác định có phải class không đội mũ bằng `is_no_helmet_class()`.
   - Vẽ bounding box.
   - Ghi confidence lên ảnh bằng `draw_confidence_label()`.
6. Nếu phát hiện vi phạm đủ điều kiện, app lưu ảnh bằng chứng.
7. `save_violation_evidence()` tính SHA-256, tạo IPFS URI, ghi Blockchain/local-chain và lưu SQLite.
8. `send_telegram_alert_async()` gửi cảnh báo Telegram nếu đã cấu hình.
9. Streamlit hiển thị ảnh kết quả và thống kê.

## 6. Luồng hoạt động khi xử lý video

Khi người dùng upload video:

1. Streamlit lưu video vào file tạm.
2. `process_video()` mở video bằng `cv2.VideoCapture`.
3. App đọc từng frame.
4. Có thể bỏ qua một số frame bằng tham số `skip_frames` để tăng tốc.
5. Frame được resize về `640x640`.
6. YOLO nhận diện trên frame.
7. `draw_boxes()` vẽ box và lưu bằng chứng nếu phát hiện vi phạm.
8. App cập nhật progress bar.
9. App tính thống kê:
   - Tổng object.
   - Có mũ.
   - Không mũ.
   - Tỷ lệ an toàn.
   - Số frame đã xử lý.
   - FPS trung bình.
10. App lưu thống kê vào `st.session_state.report_data`.

## 7. Các hàm chính trong `main.py`

### `ensure_streamlit_runtime()`

Đảm bảo nếu chạy trực tiếp:

```bash
python app/main.py
```

thì script sẽ tự chuyển sang:

```bash
streamlit run app/main.py
```

Hàm này giúp tránh lỗi do chạy Streamlit app bằng Python thường.

### `load_css()`

Inject CSS tùy chỉnh cho giao diện:

- Nền app.
- Sidebar.
- Dashboard metric.
- Tabs.
- Button.
- File uploader.
- Heading.

### `load_model()`

Tải model YOLO:

```python
YOLO("weights/best_helmet3.pt")
```

Hàm có decorator:

```python
@st.cache_resource
```

Nhờ vậy model chỉ tải một lần, không tải lại sau mỗi lần Streamlit rerun.

### `init_violation_db()`

Tạo bảng `violations` nếu chưa tồn tại. Hàm cũng tự bổ sung các cột mới nếu database cũ thiếu:

- `image_hash`
- `blockchain_tx`
- `ipfs_uri`

Đây là phần migration đơn giản cho SQLite.

### `calculate_sha256(file_path)`

Đọc file ảnh theo từng chunk và tính SHA-256:

```python
sha256.update(chunk)
```

Dùng cho:

- Lưu hash ảnh bằng chứng.
- Xác thực lại ảnh sau này.

### `is_blockchain_configured()`

Kiểm tra đủ cấu hình Blockchain hay chưa:

```python
BLOCKCHAIN_RPC_URL
BLOCKCHAIN_PRIVATE_KEY
BLOCKCHAIN_CONTRACT_ADDRESS
```

Nếu thiếu một trong các biến này, app chạy chế độ local.

### `register_hash_on_blockchain(evidence_hash, image_path, ipfs_uri)`

Ghi hash ảnh lên smart contract nếu đã cấu hình Blockchain.

Nếu chưa cấu hình, hàm trả về mã local:

```text
local-chain:<16 ký tự đầu của SHA-256>
```

Nếu cấu hình Blockchain thật, hàm:

1. Kết nối RPC bằng Web3.
2. Tạo account từ private key.
3. Tạo contract object từ ABI và contract address.
4. Build transaction gọi `registerViolation`.
5. Ký transaction.
6. Gửi transaction.
7. Trả về transaction hash.

### `build_ipfs_uri(evidence_hash)`

Tạo IPFS URI tạm:

```text
ipfs://pending/<16 ký tự đầu của SHA-256>
```

Hiện tại đây là placeholder. Nếu tích hợp upload IPFS thật, hàm này nên được thay bằng logic upload ảnh lên IPFS và trả về CID thật.

### `save_violation_evidence(camera, violation_type, image_path, confidence, timestamp)`

Hàm trung tâm để lưu một vi phạm:

1. Tính SHA-256 của ảnh.
2. Tạo IPFS URI.
3. Ghi hash lên Blockchain hoặc tạo `local-chain`.
4. Insert bản ghi vào SQLite.
5. Trả về dict:

```python
{
    "image_hash": image_hash,
    "blockchain_tx": blockchain_tx,
    "ipfs_uri": ipfs_uri,
}
```

### `build_transaction_url(tx_hash)`

Nếu có `BLOCKCHAIN_EXPLORER_TX_URL` và `tx_hash` là hash thật bắt đầu bằng `0x`, hàm tạo link explorer.

Nếu là mã local-chain, hàm trả về nguyên chuỗi.

### `normalize_class_name(label)`

Chuẩn hóa tên class YOLO:

- Chuyển về chữ thường.
- Xóa khác biệt `_` và `-`.
- Giúp so sánh class ổn định hơn.

### `is_no_helmet_class(cls_id, label)`

Xác định một class có phải người không đội mũ hay không.

Hàm kiểm tra các từ khóa:

```text
without helmet
no helmet
nohelmet
khong mu
không mũ
```

Nếu label chứa các từ khóa có mũ như `helmet`, `with helmet`, `có mũ`, hàm trả về `False`.

Nếu không nhận diện được bằng label, hàm fallback theo `cls_id == 1`.

### `draw_confidence_label(image, x1, y1, conf, color, font_scale, thickness)`

Vẽ ô label confidence lên ảnh tại vị trí bounding box.

Hàm tự tính:

- Kích thước chữ.
- Vị trí label.
- Giới hạn label không vượt ra ngoài frame.

### `draw_boxes(image, results, actual_fps=None, font_scale_base=0.5)`

Hàm vẽ toàn bộ kết quả YOLO lên ảnh hoặc frame video.

Nhiệm vụ:

1. Duyệt từng bounding box.
2. Lấy tọa độ, confidence, class ID và label.
3. Xác định vi phạm bằng `is_no_helmet_class()`.
4. Vẽ box đỏ cho không đội mũ, xanh cho có mũ.
5. Ghi confidence.
6. Tính thống kê:
   - Tổng object.
   - Số người có mũ.
   - Số người không mũ.
   - Danh sách confidence.
7. Nếu phát hiện vi phạm đủ điều kiện, lưu ảnh bằng chứng.
8. Nếu xử lý video, vẽ overlay thống kê và FPS.

Điều kiện lưu vi phạm hiện tại:

```python
if count == 2 and violation_detected:
```

Điều này giúp giảm việc lưu quá nhiều ảnh liên tục khi video có nhiều frame vi phạm.

### `process_image(image, confidence_threshold, iou_threshold)`

Xử lý một ảnh upload:

1. Chuyển ảnh nếu có alpha channel.
2. Chạy YOLO với `confidence_threshold` và `iou_threshold`.
3. Chuyển màu phù hợp giữa RGB/BGR.
4. Gọi `draw_boxes()`.
5. Trả về ảnh đã annotate và thống kê.

### `send_telegram_alert(photo_path, caption)`

Gửi ảnh bằng chứng lên Telegram bằng Bot API:

```text
https://api.telegram.org/bot<TOKEN>/sendPhoto
```

Nếu thiếu token hoặc chat ID, hàm không gửi và cập nhật trạng thái lỗi.

### `send_telegram_alert_async(photo_path, caption)`

Gửi Telegram trong thread riêng để không chặn xử lý video.

Hàm có cooldown toàn cục:

```python
ALERT_COOLDOWN = 1
```

Mục đích là tránh gửi quá nhiều cảnh báo trong thời gian ngắn.

### `process_video(video_path, confidence_threshold, iou_threshold, skip_frames=5)`

Xử lý video upload:

1. Mở video.
2. Tạo progress bar.
3. Duyệt frame.
4. Bỏ qua frame theo `skip_frames`.
5. Resize frame.
6. Chạy YOLO.
7. Vẽ box bằng `draw_boxes()`.
8. Hiển thị frame annotated trong Streamlit.
9. Tính thống kê cuối video.
10. Lưu thống kê vào session.

### `generate_report()`

Chuyển `st.session_state.report_data` thành DataFrame để:

- Hiển thị lịch sử thống kê.
- Tải CSV.

## 8. Các hàm dùng chung trong `violation_ui.py`

### `setup_page(title, icon)`

Cấu hình một trang Streamlit phụ:

- Page title.
- Page icon.
- Layout wide.
- Sidebar mở sẵn.
- Load CSS.
- Render menu sidebar tùy chỉnh.

Các page trong `pages/` đều dùng hàm này.

### `load_css()`

CSS dùng cho các trang phụ:

- Nền app.
- Sidebar.
- Metric card.
- Detail box.
- Text hash.
- Kết quả MATCH/MISMATCH.

### `page_header(title, subtitle)`

Render tiêu đề và mô tả đầu trang bằng HTML/CSS thống nhất.

### `render_sidebar_navigation()`

Render menu trái:

```python
st.page_link("main.py", label="🏠 Dashboard")
st.page_link("pages/2_Danh_sach_vi_pham.py", label="📋 Danh sách vi phạm")
st.page_link("pages/3_Xac_thuc_SHA256.py", label="🔒 Xác thực SHA-256")
st.page_link("pages/4_Thong_ke.py", label="📊 Thống kê")
```

Hàm này thay cho sidebar nav mặc định của Streamlit để menu hiển thị đúng tiếng Việt có dấu.

### `load_violations()`

Đọc toàn bộ bảng `violations`:

```sql
SELECT * FROM violations ORDER BY id DESC
```

Hàm có cache:

```python
@st.cache_data(ttl=5)
```

Vì vậy dữ liệu được cache trong 5 giây để giảm truy vấn SQLite lặp lại.

### `normalize_df(df)`

Chuẩn hóa DataFrame vi phạm:

- Parse `timestamp` thành datetime.
- Tạo cột `timestamp_dt`.
- Tạo cột `date`.
- Tạo cột `display_time` dạng `dd/mm/yyyy hh:mm:ss`.

Các page dùng cột `display_time` để hiển thị thời gian đẹp hơn.

### `resolve_image_path(path_value)`

Chuyển `image_path` trong database thành đường dẫn thật.

Hàm thử nhiều trường hợp:

- Đường dẫn tuyệt đối.
- Đường dẫn tương đối theo `app/`.
- Đường dẫn tương đối theo thư mục gốc repo.
- Đường dẫn raw ban đầu.

Điều này giúp app vẫn tìm được ảnh khi database lưu path theo nhiều kiểu khác nhau.

### `calculate_sha256(file_path)`

Tính SHA-256 của ảnh bằng chứng. Hàm này giống logic trong `main.py`, dùng cho các trang xác thực.

### `has_text(value)`

Trả về mask boolean để kiểm tra cột có giá trị text thật hay không.

Dùng để đếm:

- Bản ghi đã có hash.
- Bản ghi đã có Blockchain TX.

### `dashboard_counts(df)`

Tính các số liệu dashboard:

```python
{
    "total": tổng số vi phạm,
    "hashed": số bản ghi có image_hash,
    "missing_hash": số bản ghi chưa có image_hash,
    "blockchain": số bản ghi có blockchain_tx,
    "today": số vi phạm trong ngày hiện tại,
}
```

### `stats_by_date(df)`

Nhóm số vi phạm theo ngày:

```text
Ngày   Số vi phạm
02/05  13
05/05  33
30/05  28
```

Dữ liệu này được dùng cho:

```python
st.bar_chart(...)
```

### `render_dashboard()`

Render toàn bộ trang Dashboard phụ:

- Gọi `setup_page()`.
- Gọi `load_violations()`.
- Tính `dashboard_counts()`.
- Hiển thị metric.
- Hiển thị bảng vi phạm gần nhất.
- Hiển thị biểu đồ thống kê theo ngày.

## 9. Công cụ dòng lệnh `query_violations.py`

File này dùng để truy vấn SQLite ngoài giao diện Streamlit.

Xem thống kê:

```bash
python app/query_violations.py stats
```

Xem vi phạm mới nhất:

```bash
python app/query_violations.py latest --limit 10
```

Xem dòng chưa có hash:

```bash
python app/query_violations.py missing-hash
```

Thống kê theo ngày:

```bash
python app/query_violations.py by-date
```

Xem chi tiết theo ID:

```bash
python app/query_violations.py detail 1
```

Tìm theo hash hoặc Blockchain TX:

```bash
python app/query_violations.py search-hash 655344
```

Xác thực ảnh theo hash hoặc Blockchain TX:

```bash
python app/query_violations.py verify-image 655344
```

Các trạng thái xác thực:

| Trạng thái | Ý nghĩa |
| --- | --- |
| `MATCH` | Hash hiện tại của file ảnh trùng hash lưu trong database. |
| `MISMATCH` | Hash hiện tại khác hash trong database, ảnh có thể đã bị sửa. |
| `MISSING_FILE` | File ảnh không còn tồn tại tại `image_path`. |
| `NO_STORED_HASH` | Bản ghi chưa có hash lưu trong database. |

## 10. Cấu hình `.env`

File cấu hình:

```text
app/.env
```

Các biến Telegram:

```env
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=
```

Các biến Blockchain:

```env
BLOCKCHAIN_RPC_URL=
BLOCKCHAIN_PRIVATE_KEY=
BLOCKCHAIN_CONTRACT_ADDRESS=
BLOCKCHAIN_CHAIN_ID=
BLOCKCHAIN_EXPLORER_TX_URL=
```

Nếu không cấu hình Blockchain, app vẫn chạy local và tạo:

```text
local-chain:<16 ký tự đầu SHA-256>
```

## 11. Luồng dữ liệu tổng quát

```text
Upload ảnh/video
    ↓
YOLO nhận diện
    ↓
draw_boxes() vẽ bounding box
    ↓
Phát hiện "không đội mũ"
    ↓
Lưu ảnh vào app/violations/
    ↓
calculate_sha256()
    ↓
build_ipfs_uri()
    ↓
register_hash_on_blockchain()
    ↓
save_violation_evidence()
    ↓
Insert vào app/violations.db
    ↓
Dashboard / Danh sách / Xác thực / Thống kê đọc lại từ SQLite
```

## 12. Cách kiểm tra nhanh app

Kiểm tra cú pháp:

```bash
conda run -n robot_env python -m compileall app/main.py app/violation_ui.py app/pages
```

Chạy app:

```bash
conda run -n robot_env streamlit run app/main.py
```

Kiểm tra database có dữ liệu:

```bash
sqlite3 app/violations.db "SELECT COUNT(*) FROM violations;"
```

Xem bản ghi mới nhất:

```bash
sqlite3 app/violations.db "SELECT id, timestamp, image_hash, blockchain_tx FROM violations ORDER BY id DESC LIMIT 5;"
```

## 13. Gợi ý khi phát triển tiếp

Một số hướng có thể mở rộng:

- Thay `build_ipfs_uri()` bằng upload IPFS thật.
- Tách logic YOLO, database, Telegram, Blockchain thành service riêng để `main.py` gọn hơn.
- Thêm filter theo ngày trong trang danh sách.
- Thêm export CSV cho bảng vi phạm trong database.
- Thêm trạng thái xác thực Blockchain thật cho từng transaction.
- Thêm phân quyền nếu app dùng trong môi trường sản xuất.
