import os
import base45
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
scan_is_done = False

def scan_qr_code_and_start_process():
    cap = cv2.VideoCapture(0)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    print("Camera has started. Press 'q' to exit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("No camera data.")
            break

        results = zxingcpp.read_barcodes(
            frame,
            formats=zxingcpp.BarcodeFormat.QRCode,
            try_rotate=True
        )

        for result in results:
            text = result.text
            decode_qr_code(text)

        cv2.imshow("Version-40 Live QR Code Scanner", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def decode_qr_code(text):
    parameters=text.split('|')
    scanned_qr_code=None
    if len(parameters)==5:
        scanned_qr_code=QrCode("hdr", parameters[1], parameters[2], parameters[3], parameters[4], None, None)
    else:
        chunk_payload = text[4:]
        packet_id = text[:4]
        if packet_id.isdigit():
            packet_id = int(packet_id)
            scanned_qr_code = QrCode("data", None, None, None, None, chunk_payload, packet_id)
        else:
            print("Invalid Packet Format")

    if scanned_qr_code is not None:
        create_dictionary_of_qr_codes(scanned_qr_code)

def create_dictionary_of_qr_codes(qr_code):
    global got_header, scan_is_done
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
            scan_is_done=True
        else:
            print(f"{round((len(dictionary_of_qr_codes)-4)/int(dictionary_of_qr_codes['total_packet_number'])*100,2)}%")
    else:
        print("Scaning proccses is started but because there is no header data, deatils are missed.")
    if scan_is_done:
        create_file_from_dict(dictionary_of_qr_codes)

def create_file_from_dict(dictionary_of_qr_codes):
    total_packets = int(dictionary_of_qr_codes["total_packet_number"])
    file_name = dictionary_of_qr_codes["file_name"]
    expected_size = int(dictionary_of_qr_codes.get("file_size", 0))
    output_folder = "file_output"
    missing_keys = [
        f"id_{i}" for i in range(total_packets) if f"id_{i}" not in dictionary_of_qr_codes
    ]
    if missing_keys:
        raise ValueError(
            f"There are missing packages. Total expected: {total_packets}, missed: {missing_keys}"
        )
    full_b45_str = "".join(dictionary_of_qr_codes[f"id_{i}"] for i in range(total_packets))
    raw_bytes = base45.b45decode(full_b45_str)
    if expected_size > 0 and len(raw_bytes) != expected_size:
        print(
            f"Warning: File size does not match. Expected: {expected_size}, Real: {len(raw_bytes)}"
        )
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, file_name)
    with open(output_path, "wb") as f:
        f.write(raw_bytes)
    print(
        f"The file created successfully: {output_path} ({len(raw_bytes)} byte)"
    )

if __name__ == '__main__':
    scan_qr_code_and_start_process()
