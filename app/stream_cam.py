import cv2
import requests
import time

STREAM_URL = "http://192.168.1.91:8080/video"
SERVER_URL = "http://127.0.0.1:8000/upload"   # đổi IP server nếu khác máy
SEND_INTERVAL = 5   # giây
CAMERA_NAME = "PhoneCam"

cap = cv2.VideoCapture(STREAM_URL)

if not cap.isOpened():
    print("Không kết nối được stream")
    exit()

last_send_time = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("Mất frame")
        break

    cv2.imshow("Phone Stream", frame)

    current_time = time.time()

    # gửi mỗi N giây
    if current_time - last_send_time >= SEND_INTERVAL:
        temp_path = "temp.jpg"
        cv2.imwrite(temp_path, frame)

        with open(temp_path, "rb") as f:
            files = {"image": ("temp.jpg", f, "image/jpeg")}
            data = {"camera": CAMERA_NAME}

            try:
                response = requests.post(SERVER_URL, files=files, data=data, timeout=30)
                print("Server response:", response.json())
            except Exception as e:
                print("Send error:", e)

        last_send_time = current_time

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()