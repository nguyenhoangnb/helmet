import time
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image

# ================= CONFIG =================
TARGET_NAME = "Hoàng BK"        # 🔥 sửa
IMAGE_PATH = "/home/hoang/yolo-helmet-detections/app/violations/violation_20260502_213815.jpg"   # 🔥 sửa
PROFILE_PATH = "./zalo_profile"
# ==========================================


def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={PROFILE_PATH}")  # lưu session

    driver = webdriver.Chrome(options=options)
    driver.get("https://chat.zalo.me/")
    return driver


def wait_login():
    print("👉 Nếu chưa login thì quét QR (20s)...")
    time.sleep(20)


def find_and_open_chat(driver, name):
    wait = WebDriverWait(driver, 20)

    print("🔍 Đang tìm ô search...")

    # 🔥 tìm input tổng quát (không phụ thuộc placeholder)
    search_box = wait.until(
        EC.presence_of_element_located((
            By.XPATH, '//input[@type="text"]'
        ))
    )

    search_box.clear()
    search_box.send_keys(name)

    time.sleep(0.2)

    print("👤 Đang chọn người chat...")

    user = wait.until(
        EC.element_to_be_clickable((
            By.XPATH, '//div[contains(@class,"conv-item")]'
        ))
    )
    user.click()

    time.sleep(0.1)


def send_text(driver, text):
    wait = WebDriverWait(driver, 20)

    print("💬 Đang gửi text...")

    msg_box = wait.until(
        EC.presence_of_element_located((
            By.XPATH, '//div[@contenteditable="true"]'
        ))
    )

    msg_box.send_keys(text)
    msg_box.send_keys(Keys.ENTER)

    time.sleep(1)

def copy_image_to_clipboard(image_path):
    # 🔥 copy trực tiếp ảnh (PNG/JPG)
    os.system(f"xclip -selection clipboard -t image/png -i {image_path}")

# def send_image(driver, image_path):
#     from selenium.webdriver.common.action_chains import ActionChains

#     wait = WebDriverWait(driver, 20)

#     if not os.path.exists(image_path):
#         print("❌ Không tìm thấy ảnh:", image_path)
#         return

#     print("📋 Copy ảnh vào clipboard...")
#     copy_image_to_clipboard(image_path)

#     msg_box = wait.until(
#         EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]'))
#     )

#     print("🎯 Focus vào chat box...")
#     msg_box.click()
#     time.sleep(0.1)

#     # 🔥 CLICK thêm lần nữa cho chắc chắn focus
#     ActionChains(driver).move_to_element(msg_box).click().perform()
#     time.sleep(0.1)

#     print("📤 Paste ảnh (Ctrl+Shift+V)...")
#     msg_box.send_keys(Keys.CONTROL, 'v')   # 🔥 QUAN TRỌNG

#     time.sleep(0.1)

#     # 🔥 check preview ảnh (rất quan trọng)
#     previews = driver.find_elements(By.XPATH, '//img[contains(@src,"blob")]')

#     if len(previews) == 0:
#         print("❌ Không thấy preview → paste fail")
#         return
#     else:
#         print("✅ Có preview ảnh")

#     print("📨 Gửi ảnh...")
#     msg_box.send_keys(Keys.ENTER)

#     print("✅ Đã gửi ảnh")

def get_msg_box(driver):
    
    wait = WebDriverWait(driver, 20)
    return wait.until(
        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]'))
    )

def send_image(driver, image_path):
    from selenium.webdriver.common.action_chains import ActionChains


    if not os.path.exists(image_path):
        print("❌ Không tìm thấy ảnh")
        return

    print("📋 Copy clipboard...")
    copy_image_to_clipboard(image_path)

    # 🔥 luôn lấy lại element mới
    msg_box = get_msg_box(driver)

    msg_box.click()
    time.sleep(0.5)

    ActionChains(driver).move_to_element(msg_box).click().perform()
    time.sleep(0.5)

    print("📤 Paste...")
    msg_box = get_msg_box(driver)   # 🔥 lấy lại
    msg_box.send_keys(Keys.CONTROL, 'v')

    time.sleep(2)

    previews = driver.find_elements(By.XPATH, '//img[contains(@src,"blob")]')

    if len(previews) == 0:
        print("❌ Paste fail")
        return

    print("📨 Send...")

    msg_box = get_msg_box(driver)   # 🔥 lấy lại lần nữa
    msg_box.send_keys(Keys.ENTER)

    print("✅ Done")

# ================= MAIN =================
if __name__ == "__main__":
    driver = init_driver()

    # wait_login()

    try:
        find_and_open_chat(driver, TARGET_NAME)

        # send_text(driver, "Test gửi từ Python")
        # copy_image_to_clipboard(IMAGE_PATH)

        send_image(driver, IMAGE_PATH)
        time.sleep(5)
        send_image(driver, IMAGE_PATH)

        print("✅ DONE")

    except Exception as e:
        print("❌ Lỗi:", e)

    # giữ browser để debug
    time.sleep(1)
    # input("Nhấn Enter để thoát...")