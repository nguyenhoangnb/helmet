import cv2
import requests
import time

VIDEO_PATH = "video.mp4" # đường dẫn đến video cần phát
SERVER_URL = "http://127.0.0.1:8000/upload"
SEND_INTERVAL = 5   # giây trong video thường có tốc độ khung hình cao hơn, nên ta sẽ gửi mỗi N giây thay vì mỗi frame
CAMERA_NAME = "VideoCam"

cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    print("Không mở được video")
    exit()

last_send_time = 0

while True:
    ret, frame = cap.read()

    if not ret:
        print("Hết video")
        break

    cv2.imshow("Video", frame)

    current_time = time.time()

    if current_time - last_send_time >= SEND_INTERVAL:
        # encode ảnh trực tiếp (không cần lưu file)
        _, img_encoded = cv2.imencode('.jpg', frame)

        files = {
            "image": ("frame.jpg", img_encoded.tobytes(), "image/jpeg")
        }
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