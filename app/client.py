import requests

SERVER_URL = "http://127.0.0.1:8000/upload"   # đổi IP nếu cần
IMAGE_PATH = "/home/hoang/yolo-helmet-detections/test_images/12.jpeg"                       # ảnh cần gửi
CAMERA_NAME = "Camera_01"

def send_image():
    with open(IMAGE_PATH, "rb") as img:
        files = {
            "image": (IMAGE_PATH, img, "image/jpeg")
        }

        data = {
            "camera": CAMERA_NAME
        }

        response = requests.post(SERVER_URL, files=files, data=data)

    print("Status code:", response.status_code)
    print("Response:", response.json())

if __name__ == "__main__":
    send_image()