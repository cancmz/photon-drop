import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget
from transmit_tab import TransmitTab
from receive_tab import ReceiveTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photondrop")
        self.resize(540, 648)
        self.setMinimumSize(540, 648)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.transmit_tab = TransmitTab()
        self.receive_tab = ReceiveTab()

        self.tabs.addTab(self.transmit_tab, "Transmit")
        self.tabs.addTab(self.receive_tab, "Receive")

def main():
    app = QApplication(sys.argv)

    app.setStyle("Material")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    # Windows ("spawn") ve PyInstaller icin sart: worker process'ler uygulamayi
    # yeniden baslatmasin.
    import multiprocessing
    multiprocessing.freeze_support()
    main()