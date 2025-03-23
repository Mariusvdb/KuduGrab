import sys
import os
import json
import traceback
import subprocess  # For opening folder
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QComboBox, QRadioButton, QFileDialog
from PyQt5.QtCore import Qt, QRect, QPoint, QTimer
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QScreen, QCursor, QImage, QIcon

# Version number
APP_VERSION = "v1.0.0"

# Load config file
CONFIG_FILE = "config.json"
DEFAULT_SIZES = [768, 640, 640, 512, 480, 320]

def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                sizes = config.get("sizes", DEFAULT_SIZES)
                default_w = config.get("default_w", 800)
                default_h = config.get("default_h", 600)
                save_location = config.get("save_location", os.getcwd())  # Load saved location
                print(f"Loaded config: sizes={sizes}, default_w={default_w}, default_h={default_h}, save_location={save_location}")
                return sizes, default_w, default_h, save_location
        print("No config file found, using defaults")
        return DEFAULT_SIZES, 800, 600, os.getcwd()
    except Exception as e:
        print(f"Error loading config: {e}")
        return DEFAULT_SIZES, 800, 600, os.getcwd()

def save_config(sizes, default_w, default_h, save_location):
    try:
        config = {"sizes": sizes, "default_w": default_w, "default_h": default_h, "save_location": save_location}
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"Saved config: sizes={sizes}, default_w={default_w}, default_h={default_h}, save_location={save_location}")
    except Exception as e:
        print(f"Error saving config: {e}")

def gcd(a, b):
    while b:
        a, b = b, a % b
    return a

def simplify_ratio(w, h):
    divisor = gcd(w, h)
    return f"{w // divisor}:{h // divisor}"

class ScreenCaptureApp(QWidget):
    def __init__(self):
        super().__init__()
        try:
            print("Initializing ScreenCaptureApp...")
            self.setWindowTitle(f'KuduGrab {APP_VERSION}')
            self.setWindowIcon(QIcon('icon.png'))
            self.setGeometry(300, 300, 300, 150)  # Updated geometry
            self.is_capturing = False
            self.capture_mode = None
            self.global_begin = QPoint()
            self.global_end = QPoint()
            self.output_mode = "clipboard"
            self.sizes, self.default_w, self.default_h, self.save_location = load_config()  # Load save_location
            self.initUI()
            self.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.show()
            print("Main window initialized and should be visible")
        except Exception as e:
            print(f"Crash in __init__: {e}")
            traceback.print_exc()

    def initUI(self):
        try:
            print("Setting up UI...")
            mainLayout = QVBoxLayout()
            modeLayout = QHBoxLayout()
            buttonLayout = QHBoxLayout()
            fixedSizeLayout = QHBoxLayout()
            locationLayout = QHBoxLayout()

            # Mode selection (spread across top)
            self.clipboardRadio = QRadioButton("To Clipboard", self)
            self.clipboardRadio.setChecked(True)
            self.clipboardRadio.toggled.connect(lambda: self.set_output_mode("clipboard"))
            modeLayout.addWidget(self.clipboardRadio)
            modeLayout.addStretch(1)

            self.fixedLocationRadio = QRadioButton("To Default", self)
            self.fixedLocationRadio.toggled.connect(lambda: self.set_output_mode("fixed_location"))
            modeLayout.addWidget(self.fixedLocationRadio)
            modeLayout.addStretch(1)

            self.newLocationRadio = QRadioButton("New Location", self)
            self.newLocationRadio.toggled.connect(lambda: self.set_output_mode("new_location"))
            modeLayout.addWidget(self.newLocationRadio)
            modeLayout.addStretch(1)

            # Free Hand Capture and MP/Ratio centered over switch
            self.captureBtn = QPushButton('Free Hand Capture', self)
            self.captureBtn.clicked.connect(self.start_freehand_capture)
            self.captureBtn.setFixedHeight(20)
            self.captureBtn.setFixedWidth(120)
            self.captureBtn.setStyleSheet("font-size: 10px; font-weight: bold;")
            buttonLayout.addWidget(self.captureBtn)
            buttonLayout.addStretch(1)

            # Nested layout for MP and Ratio centering
            infoLayout = QHBoxLayout()
            self.mpLabel = QLabel(self)
            self.ratioLabel = QLabel(self)
            infoLayout.addWidget(self.mpLabel)
            infoLayout.addWidget(self.ratioLabel)
            buttonLayout.addLayout(infoLayout)
            buttonLayout.addStretch(1)

            # Fixed Size Capture and W/H selection (reordered)
            self.fixedCaptureBtn = QPushButton('Fixed Size Capture', self)
            self.fixedCaptureBtn.clicked.connect(self.start_fixed_capture)
            self.fixedCaptureBtn.setFixedHeight(20)
            self.fixedCaptureBtn.setFixedWidth(120)
            self.fixedCaptureBtn.setStyleSheet("font-size: 10px; font-weight: bold;")
            
            widthLabel = QLabel("W:", self)
            self.widthInput = QComboBox(self)
            self.widthInput.addItems([str(size) for size in self.sizes])
            self.widthInput.setCurrentText(str(self.default_w))
            self.widthInput.currentTextChanged.connect(self.update_info_labels)
            self.widthInput.setFixedHeight(20)

            self.swapBtn = QPushButton('<>', self)
            self.swapBtn.setFixedSize(20, 20)
            self.swapBtn.clicked.connect(self.swap_dimensions)
            self.swapBtn.setStyleSheet("font-size: 12px;")

            heightLabel = QLabel("H:", self)
            self.heightInput = QComboBox(self)
            self.heightInput.addItems([str(size) for size in self.sizes])
            self.heightInput.setCurrentText(str(self.default_h))
            self.heightInput.currentTextChanged.connect(self.update_info_labels)
            self.heightInput.setFixedHeight(20)

            fixedSizeLayout.addWidget(self.fixedCaptureBtn)
            fixedSizeLayout.addWidget(widthLabel)
            fixedSizeLayout.addWidget(self.widthInput)
            fixedSizeLayout.addWidget(self.swapBtn)
            fixedSizeLayout.addWidget(self.heightInput)  # H dropdown before H: label
            fixedSizeLayout.addWidget(heightLabel)       # H: label after dropdown
            fixedSizeLayout.addStretch(1)

            # Location selection with folder buttons
            self.locationLabel = QLabel(f"📁 {self.save_location}", self)
            self.locationLabel.setStyleSheet("font-size: 9px;")
            
            self.setLocationButton = QPushButton('📁 set', self)  # Folder icon and "set"
            self.setLocationButton.clicked.connect(self.set_save_location)
            self.setLocationButton.setFixedHeight(22)
            self.setLocationButton.setFixedWidth(50)
            self.setLocationButton.setStyleSheet("font-size: 9px;")
            
            self.getLocationButton = QPushButton('📁 get', self)  # Folder icon and "get"
            self.getLocationButton.clicked.connect(self.open_save_location)
            self.getLocationButton.setFixedHeight(22)
            self.getLocationButton.setFixedWidth(50)
            self.getLocationButton.setStyleSheet("font-size: 9px;")
            
            locationLayout.addWidget(self.locationLabel)
            locationLayout.addWidget(self.setLocationButton)
            locationLayout.addWidget(self.getLocationButton)
            locationLayout.addStretch(1)

            mainLayout.addLayout(modeLayout)
            mainLayout.addStretch(1)
            mainLayout.addLayout(buttonLayout)
            mainLayout.addLayout(fixedSizeLayout)
            mainLayout.addLayout(locationLayout)
            mainLayout.addStretch(1)
            
            self.setLayout(mainLayout)
            self.update_info_labels()
            print("UI setup complete")
        except Exception as e:
            print(f"Crash in initUI: {e}")
            traceback.print_exc()

    def update_info_labels(self):
        try:
            w = int(self.widthInput.currentText())
            h = int(self.heightInput.currentText())
            mp = (w * h) / 1000000
            ratio = simplify_ratio(w, h)
            self.mpLabel.setText(f"{mp:.2f} MP")
            self.ratioLabel.setText(f"Ratio: {ratio}")
            self.mpLabel.setStyleSheet("font-size: 9px;")
            self.ratioLabel.setStyleSheet("font-size: 9px;")
        except Exception as e:
            print(f"Error in update_info_labels: {e}")

    def swap_dimensions(self):
        try:
            w = self.widthInput.currentText()
            h = self.heightInput.currentText()
            self.widthInput.setCurrentText(h)
            self.heightInput.setCurrentText(w)
            self.update_info_labels()
        except Exception as e:
            print(f"Error in swap_dimensions: {e}")

    def start_fixed_capture(self):
        try:
            print("Starting fixed-size capture process...")
            width = int(self.widthInput.currentText())
            height = int(self.heightInput.currentText())
            self.default_w = width
            self.default_h = height
            save_config(self.sizes, self.default_w, self.default_h, self.save_location)  # Save with location
            self.capture_mode = "fixed"
            self.hide()
            QApplication.processEvents()
            QTimer.singleShot(200, lambda: self._create_overlays(width=width, height=height))
        except Exception as e:
            print(f"Error in start_fixed_capture: {e}")
            self.show()

    def start_freehand_capture(self):
        try:
            print("Starting free-hand capture process...")
            self.capture_mode = "freehand"
            self.hide()
            QApplication.processEvents()
            QTimer.singleShot(200, self._create_overlays)
        except Exception as e:
            print(f"Error in start_freehand_capture: {e}")
            self.show()

    def _create_overlays(self, width=800, height=600):
        try:
            self.overlays = []
            self.screenshots = {}
            screens = QApplication.screens()
            for i, screen in enumerate(screens):
                overlay = OverlayWidget(self, screen, mode=self.capture_mode, fixed_width=width, fixed_height=height)
                self.overlays.append(overlay)
                overlay.show()
                overlay.update()
                self.screenshots[i] = {
                    'geometry': screen.geometry(),
                    'pixmap': screen.grabWindow(0)
                }
                print(f"Overlay {i} created for screen at {screen.geometry().x()},{screen.geometry().y()} {screen.geometry().width()}x{screen.geometry().height()}")
            self.is_capturing = True
        except Exception as e:
            print(f"Error creating overlays: {e}")
            self.show()

    def update_all_overlays(self):
        for overlay in self.overlays:
            overlay.update()

    def finish_capture(self):
        try:
            x1 = min(self.global_begin.x(), self.global_end.x()) - 1
            y1 = min(self.global_begin.y(), self.global_end.y()) - 1
            x2 = max(self.global_begin.x(), self.global_end.x()) + 1
            y2 = max(self.global_end.y(), self.global_end.y()) + 1
            print(f"Capturing from global: ({x1},{y1}) to ({x2},{y2})")
            if x2 - x1 > 10 and y2 - y1 > 10:
                selection = QPixmap(x2 - x1, y2 - y1)
                painter = QPainter(selection)
                selection_rect = QRect(x1, y1, x2 - x1, y2 - y1)
                for i, screen_data in self.screenshots.items():
                    geom = screen_data['geometry']
                    pixmap = screen_data['pixmap']
                    overlap = selection_rect.intersected(geom)
                    if not overlap.isEmpty():
                        src_x = overlap.x() - geom.x()
                        src_y = overlap.y() - geom.y()
                        dst_x = overlap.x() - x1
                        dst_y = overlap.y() - y1
                        painter.drawPixmap(dst_x, dst_y, pixmap, src_x, src_y, overlap.width(), overlap.height())
                painter.end()

                if self.output_mode == "clipboard":
                    image = selection.toImage()
                    QApplication.clipboard().setImage(image)
                elif self.output_mode == "fixed_location":
                    filename = f"capture_{x1}_{y1}_{x2-x1}x{y2-y1}.png"
                    filepath = os.path.join(self.save_location, filename)
                    counter = 1
                    while os.path.exists(filepath):
                        filename = f"capture_{x1}_{y1}_{x2-x1}x{y2-y1}_{counter}.png"
                        filepath = os.path.join(self.save_location, filename)
                        counter += 1
                    selection.save(filepath, "PNG")
                else:  # new_location
                    filepath, _ = QFileDialog.getSaveFileName(self, "Save Capture", os.path.join(self.save_location, f"capture_{x1}_{y1}_{x2-x1}x{y2-y1}.png"), "PNG Files (*.png)")
                    if filepath:
                        selection.save(filepath, "PNG")
            
            for overlay in self.overlays:
                overlay.close()
            self.overlays = []
            self.is_capturing = False
            self.global_begin = QPoint()
            self.global_end = QPoint()
            self.show()
        except Exception as e:
            print(f"Error in finish_capture: {e}")
            self.show()

    def set_output_mode(self, mode):
        try:
            self.output_mode = mode
            print(f"Output mode set to: {mode}")
            self.setLocationButton.setEnabled(mode == "fixed_location")
            self.getLocationButton.setEnabled(mode == "fixed_location")
        except Exception as e:
            print(f"Error in set_output_mode: {e}")

    def set_save_location(self):
        try:
            folder = QFileDialog.getExistingDirectory(self, "Select Save Location", self.save_location)
            if folder:
                self.save_location = folder
                self.locationLabel.setText(f"📁: {self.save_location}")
                save_config(self.sizes, self.default_w, self.default_h, self.save_location)  # Save new location
                print(f"Save location set to: {self.save_location}")
        except Exception as e:
            print(f"Error in set_save_location: {e}")

    def open_save_location(self):
        try:
            if os.path.exists(self.save_location):
                # Platform-specific folder opening
                if sys.platform == "win32":
                    os.startfile(self.save_location)
                elif sys.platform == "darwin":  # macOS
                    subprocess.run(["open", self.save_location])
                else:  # Linux
                    subprocess.run(["xdg-open", self.save_location])
                print(f"Opened save location: {self.save_location}")
            else:
                print(f"Save location does not exist: {self.save_location}")
        except Exception as e:
            print(f"Error in open_save_location: {e}")

class OverlayWidget(QWidget):
    def __init__(self, parent, screen, mode="freehand", fixed_width=800, fixed_height=600):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        try:
            self.parent = parent
            self.screen = screen
            self.is_drawing = False
            self.mode = mode
            self.fixed_width = fixed_width
            self.fixed_height = fixed_height
            
            geom = screen.geometry()
            self.setGeometry(geom)
            print(f"Overlay widget geometry: {geom.x()},{geom.y()} {geom.width()}x{geom.height()}")
            
            self.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
            self.setCursor(Qt.CrossCursor)
            self.setMouseTracking(True)
            self.setAttribute(Qt.WA_TranslucentBackground)

            instruction_text = "Click and drag to select an area, then release to capture" if mode == "freehand" else f"Click to place a {fixed_width}×{fixed_height} capture area"
            self.instructions = QLabel(instruction_text, self)
            self.instructions.setAlignment(Qt.AlignCenter)
            self.instructions.setStyleSheet("background-color: rgba(0, 0, 0, 180); color: white; padding: 10px; border-radius: 5px; font-size: 14px;")
            self.instructions.adjustSize()
            self.instructions.move((geom.width() - self.instructions.width()) // 2, 20)

            if mode == "fixed":
                self.update_timer = QTimer(self)
                self.update_timer.timeout.connect(self.update)
                self.update_timer.start(50)
        except Exception as e:
            print(f"Error in OverlayWidget __init__: {e}")

    def paintEvent(self, event):
        try:
            qp = QPainter(self)
            qp.setClipRect(self.rect())
            
            screen_geom = self.screen.geometry()
            screenshot = self.parent.screenshots[self.parent.overlays.index(self)]['pixmap']
            qp.drawPixmap(0, 0, screenshot)

            if self.mode == "fixed" and self.parent.is_capturing:
                global_pos = QCursor.pos()
                local_x = global_pos.x() - screen_geom.x()
                local_y = global_pos.y() - screen_geom.y()
                rect = QRect(local_x - self.fixed_width // 2, local_y - self.fixed_height // 2, self.fixed_width, self.fixed_height)

                if rect.intersects(self.rect()):
                    qp.fillRect(self.rect(), QColor(0, 0, 0, 30))
                    qp.setPen(QPen(QColor(255, 0, 0), 2))
                    qp.drawRect(rect)
                    print(f"Drawing fixed rect at: {rect.x()},{rect.y()} {rect.width()}x{rect.height()} on screen {screen_geom.x()},{screen_geom.y()}")

                    width, height = rect.width(), rect.height()
                    size_text = f"{width} × {height}"
                    qp.setPen(QColor(255, 255, 0))
                    text_x = rect.right() + 5 if rect.right() + 100 < self.width() else rect.left() - 100
                    text_y = rect.bottom() + 20 if rect.bottom() + 30 < self.height() else rect.top() - 10
                    text_rect = QRect(text_x - 2, text_y - 15, len(size_text) * 8 + 4, 20)
                    qp.fillRect(text_rect, QColor(0, 0, 0, 180))
                    qp.drawText(text_x, text_y, size_text)

            elif self.mode == "freehand" and not self.parent.global_begin.isNull() and not self.parent.global_end.isNull():
                begin_local = self.parent.global_begin - screen_geom.topLeft()
                end_local = self.parent.global_end - screen_geom.topLeft()
                rect = QRect(begin_local, end_local).normalized()

                if rect.intersects(self.rect()):
                    qp.fillRect(self.rect(), QColor(0, 0, 0, 30))
                    qp.setPen(QPen(QColor(255, 0, 0), 2))
                    qp.drawRect(rect)
                    print(f"Drawing freehand rect at: {rect.x()},{rect.y()} {rect.width()}x{rect.height()} on screen {screen_geom.x()},{screen_geom.y()}")

                    width, height = rect.width(), rect.height()
                    size_text = f"{width} × {height}"
                    qp.setPen(QColor(255, 255, 0))
                    text_x = rect.right() + 5 if rect.right() + 100 < self.width() else rect.left() - 100
                    text_y = rect.bottom() + 20 if rect.bottom() + 30 < self.height() else rect.top() - 10
                    text_rect = QRect(text_x - 2, text_y - 15, len(size_text) * 8 + 4, 20)
                    qp.fillRect(text_rect, QColor(0, 0, 0, 180))
                    qp.drawText(text_x, text_y, size_text)
        except Exception as e:
            print(f"Error in paintEvent: {e}")

    def mousePressEvent(self, event):
        try:
            if event.button() == Qt.LeftButton:
                global_pos = QCursor.pos()
                screen_geom = self.screen.geometry()
                print(f"Mouse press in mode: {self.mode} at global: {global_pos.x()},{global_pos.y()}")
                if self.mode == "fixed" and self.parent.is_capturing:
                    if hasattr(self, 'update_timer'):
                        self.update_timer.stop()
                    local_x = global_pos.x() - screen_geom.x()
                    local_y = global_pos.y() - screen_geom.y()
                    print(f"Fixed mode click at global: {global_pos.x()},{global_pos.y()} local: {local_x},{local_y} on screen {screen_geom.x()},{screen_geom.y()}")
                    rect = QRect(local_x - self.fixed_width // 2, local_y - self.fixed_height // 2, self.fixed_width, self.fixed_height)
                    self.parent.global_begin = rect.topLeft() + screen_geom.topLeft()
                    self.parent.global_end = rect.bottomRight() + screen_geom.topLeft()
                    self.parent.finish_capture()
                elif self.mode == "freehand" and screen_geom.contains(global_pos):
                    self.parent.global_begin = global_pos
                    self.parent.global_end = global_pos
                    self.is_drawing = True
                    print(f"Freehand start at global: {global_pos.x()},{global_pos.y()} on screen {screen_geom.x()},{screen_geom.y()}")
                    self.parent.update_all_overlays()
        except Exception as e:
            print(f"Error in mousePressEvent: {e}")

    def mouseMoveEvent(self, event):
        try:
            if self.mode == "freehand" and self.is_drawing:
                self.parent.global_end = QCursor.pos()
                print(f"Freehand move to global: {self.parent.global_end.x()},{self.parent.global_end.y()} on screen {self.screen.geometry().x()},{self.screen.geometry().y()}")
                self.parent.update_all_overlays()
            elif self.mode == "fixed" and self.parent.is_capturing:
                self.update()
        except Exception as e:
            print(f"Error in mouseMoveEvent: {e}")

    def mouseReleaseEvent(self, event):
        try:
            if event.button() == Qt.LeftButton and self.mode == "freehand" and self.is_drawing:
                self.is_drawing = False
                self.parent.global_end = QCursor.pos()
                print(f"Freehand release at global: {self.parent.global_end.x()},{self.parent.global_end.y()} on screen {self.screen.geometry().x()},{self.screen.geometry().y()}")
                self.parent.finish_capture()
        except Exception as e:
            print(f"Error in mouseReleaseEvent: {e}")

    def keyPressEvent(self, event):
        try:
            if event.key() == Qt.Key_Escape:
                if hasattr(self, 'update_timer'):
                    self.update_timer.stop()
                for overlay in self.parent.overlays:
                    overlay.close()
                self.parent.overlays = []
                self.parent.is_capturing = False
                self.parent.show()
        except Exception as e:
            print(f"Error in keyPressEvent: {e}")

def main():
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        app = QApplication(sys.argv)
        print("Starting Screen Capture App...")
        screen_capture = ScreenCaptureApp()
        print("Application running. If you can't see the window, check for it in your taskbar.")
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error starting application: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    main()