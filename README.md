### TEST
```bash
streamlit run app/main.py
```

## run sever
```bash
python3 get_follower.py
```


## run stream camera
```bash
python3 stream_cam.py
```

note: có thể chọn các model để thử và sửa trong file main.py hàm load_model để test

link bcao

https://docs.google.com/document/d/1OGyP9PB3Mf1sXo3G92eeTDPp3rCS0YWb/edit?usp=sharing&ouid=117757511095384658470&rtpof=true&sd=true

### Sử dụng app IP CAMERA trên android để stream camera
thay đổi ip trong code stream_cam.py đúng với ip hiển thị trong app

### gửi qua telegram
tạo file .env trong thư mục app trong đó có: TELEGRAM_TOKEN=token
                                              TELEGRAM_CHAT_ID=chat_id

## Chạy theo video path

terminal 1:

```bash
cd app
python3 server.py
```

terminal 2:

```bash
cd app
python3 stream_video.py
```