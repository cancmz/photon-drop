import os
import cv2
import numpy as np


def read_image_utf8(file_path):
    try:
        with open(file_path, "rb") as f:
            bytes_data = f.read()
            numpy_array = np.frombuffer(bytes_data, dtype=np.uint8)
            img = cv2.imdecode(numpy_array, cv2.IMREAD_COLOR)
            return img
    except Exception as e:
        print(f"Error occurred ({file_path}): {e}")
        return None


def fast_photo_slideshow(folder_path, delay_ms=200):
    valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')

    if not os.path.exists(folder_path):
        print(f"ERROR: Specified folder not found:\n{folder_path}")
        return

    total_files = [
        f for f in os.listdir(folder_path)
        if f.lower().endswith(valid_extensions)
    ]

    if not total_files:
        print("No photos in a supported format were found in the specified folder!")
        return

    total_files.sort()

    window_name = "QR Code Shower"
    cv2.namedWindow(window_name, cv2.WINDOW_FULLSCREEN)

    i = 0
    while True:
        file_path = os.path.join(folder_path, total_files[i])

        img = read_image_utf8(file_path)

        if img is not None:
            cv2.imshow(window_name, img)

            key = cv2.waitKey(delay_ms) & 0xFF

            if key == ord('q') or key == 27:
                break
        else:
            print(f"Skipped (Image could not be read): {total_files[i]}")

        i = (i + 1) % len(total_files)

    cv2.destroyAllWindows()


if __name__ == "__main__":
    FOLDER = r"C:\Users\ASUS\PycharmProjects\photon-drop\Taşobası,_Tarsus.pdf"

    SPEED_MS = 50

    fast_photo_slideshow(FOLDER, SPEED_MS)