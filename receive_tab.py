from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt


class ReceiveTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        placeholder = QLabel("Alıcı özellikleri bir sonraki adımda buraya eklenecek.")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #888; font-size: 14px;")

        layout.addWidget(placeholder)