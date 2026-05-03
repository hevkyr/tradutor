import sys
import time
import hashlib
from dataclasses import dataclass

import mss
from PIL import Image, ImageOps, ImageFilter
import pytesseract
from deep_translator import GoogleTranslator

from PySide6.QtCore import Qt, QRect, QThread, Signal, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QMainWindow, QMessageBox, QTextEdit


@dataclass
class CaptureRegion:
    left: int
    top: int
    width: int
    height: int


class RegionSelector(QWidget):
    region_selected = Signal(object)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowFullScreen)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.start = QPoint()
        self.end = QPoint()
        self.selecting = False

    def mousePressEvent(self, event):
        self.start = event.position().toPoint()
        self.end = self.start
        self.selecting = True
        self.update()

    def mouseMoveEvent(self, event):
        if self.selecting:
            self.end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        self.end = event.position().toPoint()
        self.selecting = False
        rect = QRect(self.start, self.end).normalized()
        self.region_selected.emit(CaptureRegion(rect.x(), rect.y(), rect.width(), rect.height()))
        self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 90))
        if self.start != self.end:
            rect = QRect(self.start, self.end).normalized()
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(rect, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor(255, 0, 255), 3))
            painter.drawRect(rect)


class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.label = QLabel(self)
        self.label.setStyleSheet(
            "QLabel { color: white; background-color: rgba(20,20,20,180); border: 2px solid rgba(255,0,255,180); border-radius: 10px; padding: 10px; }"
        )
        self.label.setWordWrap(True)
        self.label.setFont(QFont("Segoe UI", 12))
        self.hide()

    def show_text(self, text, region):
        self.setGeometry(region.left, region.top, region.width, region.height)
        self.label.setGeometry(0, 0, region.width, region.height)
        self.label.setText(text)
        self.show()


class OCRWorker(QThread):
    translated = Signal(str)
    status = Signal(str)

    def __init__(self, region, interval=1.0):
        super().__init__()
        self.region = region
        self.interval = interval
        self.running = True
        self.last_hash = None
        self.last_text = ""
        self.translator = GoogleTranslator(source="auto", target="pt")

    def preprocess(self, img):
        gray = ImageOps.grayscale(img)
        gray = gray.resize((gray.width * 2, gray.height * 2))
        gray = gray.filter(ImageFilter.SHARPEN)
        return gray

    def image_hash(self, img):
        return hashlib.md5(img.tobytes()).hexdigest()

    def run(self):
        with mss.mss() as sct:
            monitor = {"left": self.region.left, "top": self.region.top, "width": self.region.width, "height": self.region.height}
            while self.running:
                shot = sct.grab(monitor)
                frame = Image.frombytes("RGB", shot.size, shot.rgb)
                processed = self.preprocess(frame)
                current_hash = self.image_hash(processed)
                if current_hash != self.last_hash:
                    self.last_hash = current_hash
                    try:
                        text = pytesseract.image_to_string(processed, lang="eng")
                        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
                        if text and text != self.last_text:
                            self.last_text = text
                            translated = self.translator.translate(text)
                            self.translated.emit(translated)
                            self.status.emit("Texto atualizado e traduzido.")
                    except Exception as e:
                        self.status.emit(f"Erro no OCR/tradução: {e}")
                time.sleep(self.interval)

    def stop(self):
        self.running = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Screen Translator MVP")
        self.resize(720, 420)
        self.region = None
        self.worker = None
        self.overlay = OverlayWindow()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.info = QLabel("Selecione uma área da tela e inicie a tradução.")
        self.info.setWordWrap(True)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)

        btn_row = QHBoxLayout()
        self.select_btn = QPushButton("Selecionar área")
        self.start_btn = QPushButton("Iniciar tradução")
        self.stop_btn = QPushButton("Parar")
        btn_row.addWidget(self.select_btn)
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)

        layout.addWidget(self.info)
        layout.addLayout(btn_row)
        layout.addWidget(QLabel("Texto traduzido:"))
        layout.addWidget(self.preview)

        self.select_btn.clicked.connect(self.select_region)
        self.start_btn.clicked.connect(self.start_translation)
        self.stop_btn.clicked.connect(self.stop_translation)

    def select_region(self):
        self.selector = RegionSelector()
        self.selector.region_selected.connect(self.on_region_selected)
        self.selector.show()

    def on_region_selected(self, region):
        self.region = region
        self.info.setText(f"Área selecionada: x={region.left}, y={region.top}, largura={region.width}, altura={region.height}")

    def start_translation(self):
        if not self.region:
            QMessageBox.warning(self, "Aviso", "Selecione uma área primeiro.")
            return
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Em execução", "A tradução já está em andamento.")
            return
        self.worker = OCRWorker(self.region, interval=1.0)
        self.worker.translated.connect(self.update_translation)
        self.worker.status.connect(self.info.setText)
        self.worker.start()
        self.info.setText("Tradução iniciada.")

    def update_translation(self, text):
        self.preview.setPlainText(text)
        self.overlay.show_text(text, self.region)

    def stop_translation(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait()
        self.overlay.hide()
        self.info.setText("Tradução parada.")

    def closeEvent(self, event):
        self.stop_translation()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
