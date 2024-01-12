import sys
from PySide6.QtWebEngineWidgets import *
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *



class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.resize(500, 800)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            # Qt.WindowType.WindowStaysOnTopHint
            Qt.WindowType.FramelessWindowHint 
            # Qt.WindowType.WindowTransparentForInput
        )
        # layout setting
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # web window setting
        web_window = QWebEngineView(self)
        web_window.page().setBackgroundColor(Qt.GlobalColor.transparent)
        web_window.load(QUrl("http://192.168.1.7:12301/Samples/TypeScript/Demo/"))
        # text edit setting
        text_edit = QTextEdit(self)
        text_edit.setFixedSize(QSize(500, 200))
        text_edit.setHtml("小鸣也爱无所事事哟~")
        text_edit.setStyleSheet(
            "background-image: url(resources/chat.png);\
            background-position: top left;\
            background-repeat: repeat-xy;\
            color: black;\
            font-size: 15px;\
            font-family: 'Microsoft YaHei';\
            padding: 8px 28px 5px;"
            )
        text_edit.setFrameStyle(0) # 0 is no visiable 
        # widget set
        layout.addWidget(text_edit)
        layout.addWidget(web_window)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()