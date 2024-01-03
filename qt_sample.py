import sys
from PySide6.QtWebEngineWidgets import *
from PySide6.QtWidgets import *
from PySide6.QtCore import *


class WebWindow(QWebEngineView):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Live2D")
        self.page().setBackgroundColor(Qt.GlobalColor.transparent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint 
            # Qt.WindowType.WindowTransparentForInput
        )
        


if __name__ == '__main__':
    app = QApplication(sys.argv)
    view = WebWindow()
    view.load(QUrl("http://192.168.1.7:12301/Samples/TypeScript/Demo/"))
    view.resize(600, 400)
    view.show()
    app.exec()