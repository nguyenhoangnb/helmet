import cv2
import asyncio
import base64
import threading
import time
from fastapi import FastAPI, WebSocket
import uvicorn

app = FastAPI()

CAMERA_INDEX = 0
STREAM_FPS = 24
JPEG_QUALITY = 70

latest_frame = None
camera_running = True
frame_lock = threading.Lock()


def camera_reader():
    global latest_frame, camera_running

    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("Cannot open camera")
        return

    print("Camera opened")

    while camera_running:
        ret, frame = cap.read()
        if ret:
            frame = cv2.resize(frame, (640, 480))
            with frame_lock:
                latest_frame = frame.copy()

        time.sleep(0.001)

    cap.release()
    print("Camera released")


async def stream_camera(websocket: WebSocket, name: str):
    await websocket.accept()
    print(f"{name} connected")

    try:
        while True:
            with frame_lock:
                frame = None if latest_frame is None else latest_frame.copy()

            if frame is None:
                await asyncio.sleep(0.1)
                continue

            ok, buffer = cv2.imencode(
                ".jpg",
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
            )

            if ok:
                jpg_base64 = base64.b64encode(buffer).decode("utf-8")
                await websocket.send_text(jpg_base64)

            await asyncio.sleep(1 / STREAM_FPS)

    except Exception as e:
        print(f"{name} disconnected: {e}")


@app.websocket("/ws/cam1")
async def ws_cam1(websocket: WebSocket):
    await stream_camera(websocket, "cam1")


@app.websocket("/ws/cam2")
async def ws_cam2(websocket: WebSocket):
    await stream_camera(websocket, "cam2")


if __name__ == "__main__":
    t = threading.Thread(target=camera_reader, daemon=True)
    t.start()

    uvicorn.run(app, host="0.0.0.0", port=8000)

    camera_running = False