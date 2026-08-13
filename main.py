import os
import sys

import cv2
import zxingcpp
class QrCode:
    def __init__(self, qr_data_type, qr_version, total_packet_number, file_size, file_name, file_data, index_number):
        self.qr_data_type = qr_data_type
        self.qr_version = qr_version
        self.total_packet_number = total_packet_number
        self.file_size = file_size
        self.file_name = file_name
        self.file_data = file_data
        self.index_number = index_number
dictionary_of_qr_codes={}
temp_dictionary_of_qr_codes={}
got_header=False
def scan_qr_code_and_start_process():
    # 0 varsayılan kameradır. Harici webcam varsa 1 veya 2 yapabilirsiniz.
    cap = cv2.VideoCapture(0)

    # Kameranın çözünürlüğünü artırıyoruz (Version 40 için yüksek çözünürlük şart)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    print("Kamera başlatıldı. Çıkmak için 'q' tuşuna basın.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Kameradan görüntü alınamadı.")
            break

        # zxing-cpp ile kare üzerindeki QR kodları tara
        results = zxingcpp.read_barcodes(
            frame,
            formats=zxingcpp.BarcodeFormat.QRCode,
            try_rotate=True
        )

        # QR kod bulunduysa ekrana ve terminale yazdır
        for result in results:
            text = result.text
            decode_qr_code(text)

        # Canlı kamera görüntüsünü göster
        cv2.imshow("Version 40 Canlı QR Okuyucu", frame)

        # 'q' tuşuna basılırsa döngüden çık
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def decode_qr_code(text):
    data=text.strip()
    parameters=data.split('|')
    scanned_qr_code=None
    if len(parameters)==5:
        scanned_qr_code=QrCode("hdr", parameters[1], parameters[2], parameters[3], parameters[4], None, None)

    elif len(parameters)==2:
        scanned_qr_code=QrCode("data", None, -1, None, None, parameters[1], parameters[0])
    else:
        print("Invalid QR code format.")

    if scanned_qr_code is not None:
        create_dictionary_of_qr_codes(scanned_qr_code)

def create_dictionary_of_qr_codes(qr_code):
    global got_header
    if qr_code.qr_data_type=="data":
        dictionary_of_qr_codes[f"id_{qr_code.index_number}"] = qr_code.file_data
    else:
        dictionary_of_qr_codes[f"qr_version"] = qr_code.qr_version
        dictionary_of_qr_codes[f"total_packet_number"] = qr_code.total_packet_number
        dictionary_of_qr_codes[f"file_name"] = qr_code.file_name
        dictionary_of_qr_codes[f"file_size"] = qr_code.file_size
        got_header=True
    if got_header:
        if len(dictionary_of_qr_codes) == int(dictionary_of_qr_codes['total_packet_number']) + 4:
            print("All datas read (100%)")
        else:
            print(f"{round((len(dictionary_of_qr_codes)-4)/int(dictionary_of_qr_codes['total_packet_number'])*100)}%")
    else:
        print("Scaning proccses is started but because there is no header data, deatils are missed.")



if __name__ == '__main__':
    scan_qr_code_and_start_process()
