from pathlib import Path
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QFileDialog, QSpinBox, QMessageBox, QSizePolicy
)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from core.encoder import QrEncoderEngine
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize

def _bytes_to_pixmap(png_bytes: bytes) -> QPixmap:
    img = QImage()
    img.loadFromData(png_bytes, "PNG")
    return QPixmap.fromImage(img)

class SquareQRLabel(QLabel):
    """A QLabel that always stays square, scales to fit available space,
    and never stretches its pixmap (crisp QR rendering)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setScaledContents(False)  # we scale manually, preserving AR
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setMinimumSize(1, 1)

    def setQrPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self._rescale()

    # --- keep the widget itself square within whatever space it's given ---
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return width  # enforce 1:1

    def sizeHint(self) -> QSize:
        # start from whatever space the parent currently offers
        side = min(self.width(), self.height()) if self.width() and self.height() else 300
        return QSize(side, side)

    def _rescale(self):
        if self._pixmap is None or self._pixmap.isNull():
            return
        side = min(self.width(), self.height())
        if side <= 0:
            return
        scaled = self._pixmap.scaled(
            side, side,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,  # avoid smoothing/blurring QR modules
        )
        super().setPixmap(scaled)

class SquareContainer(QWidget):
    """Centers a child widget as the largest square that fits."""

    def __init__(self, child: QWidget, parent=None):
        super().__init__(parent)
        self.child = child
        child.setParent(self)

    def resizeEvent(self, event):
        side = min(self.width(), self.height())
        x = (self.width() - side) // 2
        y = (self.height() - side) // 2
        self.child.setGeometry(x, y, side, side)
        super().resizeEvent(event)

class EncodeThread(QThread):
    progress = pyqtSignal(int)
    finished_pixmap_list = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, file_path: str, qr_version: int = 40):
        super().__init__()
        self.file_path = file_path
        self.encoder = QrEncoderEngine(qr_version=qr_version)
        self.is_it_encoded = None
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            file_name = Path(self.file_path).name
            # Dosya yolunu parametre olarak geçiyoruz
            raw_bytes, self.is_it_encoded = self.encoder.read_raw_bytes_and_proccess_file_comperssion(self.file_path)
            if self._is_cancelled:
                return
            chunks = self.encoder.to_base45_chunks(raw_bytes)

            total_qr_codes = len(chunks) + 1
            pixmaps: List[QPixmap] = []

            # Frame 0 = header, sonrasi data frame'leri. Hepsi tek listede; PNG'ler
            # birden fazla cekirdekte uretilir ama iter_png_bytes sirayi korur.
            payloads = [self.encoder.build_header_payload(file_name, len(raw_bytes), len(chunks))]
            payloads += [self.encoder.build_chunk_payload(i, c) for i, c in enumerate(chunks)]

            png_iter = self.encoder.iter_png_bytes(payloads)
            try:
                for done, png_bytes in enumerate(png_iter, start=1):
                    if self._is_cancelled:
                        return
                    pixmaps.append(_bytes_to_pixmap(png_bytes))
                    self.progress.emit(int((done / total_qr_codes) * 100))
            finally:
                png_iter.close()  # iptalde bekleyen islerin havuzdan temizlenmesi

            if not self._is_cancelled:
                self.finished_pixmap_list.emit(pixmaps)
        except Exception as e:
            import traceback
            traceback.print_exc()  # Hatanın tam dosya ve satır numarasını konsola basar
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

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setEnabled(True)  # her zaman aktif
        self.btn_refresh.clicked.connect(self._reset_system)
        top_layout.addWidget(self.btn_refresh)

        self.btn_play_pause = QPushButton("Stop Playing")
        self.btn_play_pause.setEnabled(False)
        self.btn_play_pause.clicked.connect(self._toggle_slideshow)
        top_layout.addWidget(self.btn_play_pause)
        layout.addLayout(top_layout)

        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Frame Range (ms):"))
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(20, 1000)
        self.spin_interval.setValue(40)
        self.spin_interval.valueChanged.connect(
            lambda v: self.timer.setInterval(v) if self.timer.isActive() else None
        )
        speed_layout.addWidget(self.spin_interval)
        layout.addLayout(speed_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.lbl_counter = QLabel("Ready when you are!")
        self.lbl_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_counter)

        self.qr_viewport = SquareQRLabel()
        self.qr_viewport.setMinimumSize(420, 420)
        self.qr_viewport.setStyleSheet("background-color: #111; border-radius: 8px;")
        self.qr_container = SquareContainer(self.qr_viewport)
        self.qr_container.setStyleSheet("background-color: transparent;")
        layout.addWidget(self.qr_container, stretch=1)
        self.qr_viewport.setText("No QR generated yet")

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
        self.qr_viewport.setQrPixmap(self.slides[self.current_idx])
        label = "HEADER" if self.current_idx == 0 else f"DATA #{self.current_idx - 1}"
        self.lbl_counter.setText(f"Frame: {self.current_idx + 1} / {len(self.slides)} [{label}]")

    def _on_error(self, msg: str):
        self.btn_select.setEnabled(True)
        self.btn_play_pause.setEnabled(False)
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

    def _reset_system(self):
        """Sistemi her durumdan (encoding, oynatma, hata, boşta) tek tuşla
        kullanıma hazır başlangıç durumuna döndürür."""
        self.timer.stop()

        if self.thread and self.thread.isRunning():
            try:
                self.thread.progress.disconnect()
                self.thread.finished_pixmap_list.disconnect()
                self.thread.error.disconnect()
            except TypeError:
                pass

            self.thread.cancel()
            self.thread.wait()

        self.thread = None
        self.slides.clear()
        self.current_idx = 0

        self.progress_bar.setValue(0)
        self.progress_bar.repaint()

        self.qr_viewport.clear()
        self.qr_viewport.setText("No QR generated yet")
        self.qr_viewport.repaint()

        self.lbl_counter.setText("Ready when you are!")

        self.btn_select.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        self.btn_play_pause.setEnabled(False)
        self.btn_play_pause.setText("Stop playing")

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
        self.thread.start()




if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = TransmitTab()
    window.setWindowTitle("Transmitter Test Penceresi")
    window.resize(540, 648)
    window.setMinimumSize(540, 648)

    window.show()

    sys.exit(app.exec())