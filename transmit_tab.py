from pathlib import Path
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QFileDialog, QSpinBox, QMessageBox
)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from core.encoder import QrEncoderEngine


def _bytes_to_pixmap(png_bytes: bytes) -> QPixmap:
    img = QImage()
    img.loadFromData(png_bytes, "PNG")
    return QPixmap.fromImage(img)


class EncodeThread(QThread):
    progress = pyqtSignal(int)
    finished_pixmap_list = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, file_path: str, qr_version: int = 40):
        super().__init__()
        self.file_path = file_path
        self.encoder = QrEncoderEngine(qr_version=qr_version)
        self.is_it_encoded = None

    def run(self):
        try:
            file_name = Path(self.file_path).name
            # Dosya yolunu parametre olarak geçiyoruz
            raw_bytes, self.is_it_encoded = self.encoder.read_raw_bytes_and_proccess_file_comperssion(self.file_path)
            chunks = self.encoder.to_base45_chunks(raw_bytes)

            total_qr_codes = len(chunks) + 1
            pixmaps: List[QPixmap] = []

            # Header Frame
            hdr_text = self.encoder.build_header_payload(file_name, len(raw_bytes), len(chunks))
            hdr_png = self.encoder.generate_qr_svg_or_png_bytes(hdr_text)
            pixmaps.append(_bytes_to_pixmap(hdr_png))
            self.progress.emit(int((1 / total_qr_codes) * 100))

            # Data Frames
            for index, chunk in enumerate(chunks):
                chunk_text = self.encoder.build_chunk_payload(index, chunk)
                png_bytes = self.encoder.generate_qr_svg_or_png_bytes(chunk_text)
                pixmaps.append(_bytes_to_pixmap(png_bytes))
                self.progress.emit(int(((index + 2) / total_qr_codes) * 100))

            self.finished_pixmap_list.emit(pixmaps)
        except Exception as e:
            self.error.emit(str(e))


class TransmitTab(QWidget):
    def __init__(self):
        super().__init__()
        self.slides: List[QPixmap] = []
        self.current_idx: int = 0  # İsim uyuşmazlığı giderildi
        self.thread: Optional[EncodeThread] = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_frame)
        self._init_ui()

    def _init_ui(self):
        # 1. layout'a 'self' parametresi verildi (Pencerenin boş gelmesini çözen kısım)
        layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        self.btn_select = QPushButton("Select a File")
        self.btn_select.clicked.connect(self._select_file)
        top_layout.addWidget(self.btn_select)

        self.btn_play_pause = QPushButton("Stop Playing")
        self.btn_play_pause.setEnabled(False)
        self.btn_play_pause.clicked.connect(self._toggle_slideshow)
        top_layout.addWidget(self.btn_play_pause)
        layout.addLayout(top_layout)

        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Frame Range (ms):"))
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(20, 1000)
        self.spin_interval.setValue(50)
        self.spin_interval.valueChanged.connect(
            lambda v: self.timer.setInterval(v) if self.timer.isActive() else None
        )
        speed_layout.addWidget(self.spin_interval)
        layout.addLayout(speed_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.lbl_counter = QLabel("Hazır")
        self.lbl_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_counter)

        self.qr_viewport = QLabel()
        self.qr_viewport.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_viewport.setMinimumSize(420, 420)
        self.qr_viewport.setStyleSheet("background-color: #111; border-radius: 8px;")
        self.qr_viewport.setScaledContents(True)
        layout.addWidget(self.qr_viewport, stretch=1)

    def _next_frame(self):
        if not self.slides:
            return
        self.current_idx = (self.current_idx + 1) % len(self.slides)
        self._show_frame()

    def _toggle_slideshow(self):
        if self.timer.isActive():
            self.timer.stop()
            self.btn_play_pause.setText("Continue")
        else:
            self.timer.start(self.spin_interval.value())
            self.btn_play_pause.setText("Stop Playing")

    def _show_frame(self):
        if not self.slides:
            return
        self.qr_viewport.setPixmap(self.slides[self.current_idx])
        label = "HEADER" if self.current_idx == 0 else f"DATA #{self.current_idx - 1}"
        self.lbl_counter.setText(f"Frame: {self.current_idx + 1} / {len(self.slides)} [{label}]")

    def _on_error(self, msg: str):
        self.btn_select.setEnabled(True)
        QMessageBox.critical(self, "Error", f"QR codes are not generated. Error details:\n{msg}")
        self.lbl_counter.setText("An error occured.")

    def _on_encoded(self, pixmaps: List[QPixmap]):
        self.slides = pixmaps
        self.current_idx = 0

        self.btn_select.setEnabled(True)
        self.btn_play_pause.setEnabled(True)
        self.btn_play_pause.setText("Stop Playing")

        self.timer.start(self.spin_interval.value())
        self._show_frame()

    def _select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if not file_path:
            return

        self.btn_select.setEnabled(False)
        self.btn_play_pause.setEnabled(False)
        self.timer.stop()
        self.progress_bar.setValue(0)
        self.lbl_counter.setText("QR Codes Are Being Generated...")

        self.thread = EncodeThread(file_path=file_path)
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.finished_pixmap_list.connect(self._on_encoded)
        self.thread.error.connect(self._on_error)

        # run() yerine start() ile thread başlatıyoruz
        self.thread.start()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = TransmitTab()
    window.setWindowTitle("Transmitter Test Penceresi")
    window.resize(500, 600)
    window.show()

    sys.exit(app.exec())