import base45
import os
import qrcode
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
import segno

QR_VERSION=40
qr_header = qrcode.QRCode(version=QR_VERSION, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)

def browse_all_files():
    # Create an invisible root window to prevent an empty Tkinter window from appearing
    root = tk.Tk()
    root.withdraw()

    # Open the file dialog box (filetypes kaldırıldı)
    file_path = filedialog.askopenfilename(title="Select a File")

    return file_path

def encode_file_to_base45(file_path):
    with open(file_path, "rb") as file:
        encoded_string=base45.b45encode(file.read()).decode("utf-8")
        return encoded_string

def bs45_to_chunks(encoded_data, qr_version=QR_VERSION):
    capacity = 1014 if qr_version == 25 else 3380
    chunks=[encoded_data[i:i+capacity] for i in range(0, len(encoded_data), capacity)]
    return chunks

def create_and_save_qr_code(chunk, file_name, file_size, output_folder):
    counter=0
    os.makedirs(output_folder, exist_ok=True)
    header_payload=f"HDR|{QR_VERSION}|{len(chunks)}|{file_size}|{file_name}"
    header_path = os.path.join(output_folder, f"{file_name}_hdr.png")
    save_one_single_qr(header_payload, header_path)
    for index, payload in enumerate(chunk):
        data_qr_path=os.path.join(output_folder, f"{file_name}_{index}.png")
        data_qr_payload = f"{index:04d}{payload}"
        save_one_single_qr(data_qr_payload, data_qr_path)
        counter+=1
        print(round(counter / len(chunk) * 100, 2))

def save_one_single_qr(payload_text, save_path, qr_version=QR_VERSION,):
    qr = segno.make(payload_text, error="m", version=40)
    qr.save(save_path, scale=4, border=2)

file_path = browse_all_files()
if file_path:
    file_name=Path(file_path).name
    file_size = os.path.getsize(file_path)
    encoded_string= encode_file_to_base45(file_path)
    chunks= bs45_to_chunks(encoded_string)
    create_and_save_qr_code(chunks, file_name, file_size, file_name)
else:
    print("No file selected.")


"""img.save(f"version_{qr_version}_qr.png")
print("Successfully generated 'version_40_qr.png' using Version 40 matrix!")"""