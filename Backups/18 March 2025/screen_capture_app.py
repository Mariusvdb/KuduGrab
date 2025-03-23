import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QSpinBox, QRadioButton, QFileDialog
from PyQt5.QtCore import Qt, QRect, QPoint, QTimer
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QScreen, QCursor, QImage

class ScreenCaptureApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Screen Capture Tool')
        self.setGeometry(300, 300, 450, 200)  # Increased size for new UI elements
        self.is_capturing = False
        self.capture_mode = None
        self.global_begin = QPoint()
        self.global_end = QPoint()
        self.output_mode = "clipboard"  # Default mode
        self.save_location = os.getcwd()  # Default save location
        self.initUI()
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.show()
        print("Main window initialized and should be visible")

    def initUI(self):
        mainLayout = QVBoxLayout()
        buttonLayout = QHBoxLayout()
        fixedSizeLayout = QHBoxLayout()
        modeLayout = QVBoxLayout()
        locationLayout = QHBoxLayout()

        # Capture buttons
        self.captureBtn = QPushButton('Free Hand Capture', self)
        self.captureBtn.clicked.connect(self.start_freehand_capture)
        self.captureBtn.setFixedHeight(30)
        self.captureBtn.setFixedWidth(120)
        self.captureBtn.setStyleSheet("font-size: 10px; font-weight: bold;")
        buttonLayout.addWidget(self.captureBtn)
        buttonLayout.addStretch(1)

        self.fixedCaptureBtn = QPushButton('Fixed Size Capture', self)
        self.fixedCaptureBtn.clicked.connect(self.start_fixed_capture)
        self.fixedCaptureBtn.setFixedHeight(30)
        self.fixedCaptureBtn.setFixedWidth(120)
        self.fixedCaptureBtn.setStyleSheet("font-size: 10px; font-weight: bold;")
        
        widthLabel = QLabel("W:")
        self.widthInput = QSpinBox()
        self.widthInput.setRange(1, 9999)
        self.widthInput.setValue(800)
        self.widthInput.setSuffix("px")
        
        heightLabel = QLabel("H:")
        self.heightInput = QSpinBox()
        self.heightInput.setRange(1, 9999)
        self.heightInput.setValue(600)
        self.heightInput.setSuffix("px")
        
        fixedSizeLayout.addWidget(self.fixedCaptureBtn)
        fixedSizeLayout.addWidget(widthLabel)
        fixedSizeLayout.addWidget(self.widthInput)
        fixedSizeLayout.addWidget(heightLabel)
        fixedSizeLayout.addWidget(self.heightInput)
        fixedSizeLayout.addStretch(1)

        # Mode selection
        self.clipboardRadio = QRadioButton("Save to Clipboard", self)
        self.clipboardRadio.setChecked(True)  # Default
        self.clipboardRadio.toggled.connect(lambda: self.set_output_mode("clipboard"))
        modeLayout.addWidget(self.clipboardRadio)

        self.fixedLocationRadio = QRadioButton("Save to Location", self)
        self.fixedLocationRadio.toggled.connect(lambda: self.set_output_mode("fixed_location"))
        modeLayout.addWidget(self.fixedLocationRadio)

        self.newLocationRadio = QRadioButton("Save New Location", self)
        self.newLocationRadio.toggled.connect(lambda: self.set_output_mode("new_location"))
        modeLayout.addWidget(self.newLocationRadio)

        # Location selection UI
        self.locationLabel = QLabel(f"Save Location: {self.save_location}", self)
        self.locationLabel.setStyleSheet("font-size: 9px;")
        self.locationButton = QPushButton("Set Location", self)
        self.locationButton.clicked.connect(self.set_save_location)
        self.locationButton.setFixedHeight(25)
        self.locationButton.setFixedWidth(100)
        self.locationButton.setStyleSheet("font-size: 9px;")
        locationLayout.addWidget(self.locationLabel)
        locationLayout.addWidget(self.locationButton)
        locationLayout.addStretch(1)

        self.statusLabel = QLabel('Select a capture mode to begin', self)
        self.statusLabel.setAlignment(Qt.AlignCenter)
        self.statusLabel.setStyleSheet("font-size: 9px;")
        
        mainLayout.addStretch(1)
        mainLayout.addLayout(buttonLayout)
        mainLayout.addLayout(fixedSizeLayout)
        mainLayout.addLayout(modeLayout)
        mainLayout.addLayout(locationLayout)
        mainLayout.addWidget(self.statusLabel)
        mainLayout.addStretch(1)
        
        self.setLayout(mainLayout)

    def set_output_mode(self, mode):
        self.output_mode = mode
        print(f"Output mode set to: {mode}")
        self.locationButton.setEnabled(mode == "fixed_location")  # Enable button only for fixed location mode

    def set_save_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Location", self.save_location)
        if folder:
            self.save_location = folder
            self.locationLabel.setText(f"Save Location: {self.save_location}")
            print(f"Save location set to: {self.save_location}")

    def start_freehand_capture(self):
        print("Starting free-hand capture process...")
        self.statusLabel.setText('Draw a selection rectangle...')
        self.capture_mode = "freehand"
        self.hide()
        QApplication.processEvents()
        QTimer.singleShot(200, self._create_overlays)

    def start_fixed_capture(self):
        print("Starting fixed-size capture process...")
        width = self.widthInput.value()
        height = self.heightInput.value()
        self.statusLabel.setText(f'Click to place {width}×{height} capture area...')
        self.capture_mode = "fixed"
        self.hide()
        QApplication.processEvents()
        QTimer.singleShot(200, lambda: self._create_overlays(width=width, height=height))

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
            self.statusLabel.setText('Error starting capture. See console.')
            self.show()

    def update_all_overlays(self):
        for overlay in self.overlays:
            overlay.update()

    def finish_capture(self):
        try:
            x1 = min(self.global_begin.x(), self.global_end.x())
            y1 = min(self.global_begin.y(), self.global_end.y())
            x2 = max(self.global_begin.x(), self.global_end.x())
            y2 = max(self.global_end.y(), self.global_begin.y())
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
                    status_message = f'Selected area ({x2-x1}×{y2-y1}) copied to clipboard!'
                elif self.output_mode == "fixed_location":
                    filename = f"capture_{x1}_{y1}_{x2-x1}x{y2-y1}.png"
                    filepath = os.path.join(self.save_location, filename)
                    counter = 1
                    while os.path.exists(filepath):
                        filename = f"capture_{x1}_{y1}_{x2-x1}x{y2-y1}_{counter}.png"
                        filepath = os.path.join(self.save_location, filename)
                        counter += 1
                    selection.save(filepath, "PNG")
                    status_message = f'Selected area ({x2-x1}×{y2-y1}) saved to {filepath}'
                else:  # new_location
                    filepath, _ = QFileDialog.getSaveFileName(self, "Save Capture", os.path.join(self.save_location, f"capture_{x1}_{y1}_{x2-x1}x{y2-y1}.png"), "PNG Files (*.png)")
                    if filepath:
                        selection.save(filepath, "PNG")
                        status_message = f'Selected area ({x2-x1}×{y2-y1}) saved to {filepath}'
                    else:
                        status_message = 'Capture canceled by user.'
            else:
                status_message = 'Selection too small, try again.'
            
            for overlay in self.overlays:
                overlay.close()
            self.overlays = []
            self.is_capturing = False
            self.global_begin = QPoint()
            self.global_end = QPoint()
            self.statusLabel.setText(status_message)
            self.show()
        except Exception as e:
            print(f"Error in finish_capture: {e}")
            self.statusLabel.setText('Error during capture. See console.')
            self.show()

class OverlayWidget(QWidget):
    def __init__(self, parent, screen, mode="freehand", fixed_width=800, fixed_height=600):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
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

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setClipRect(self.rect())
        
        screen_geom = self.screen.geometry()
        screenshot = self.parent.screenshots[self.parent.overlays.index(self)]['pixmap']
        qp.drawPixmap(0, 0, screenshot)

        if (self.mode == "fixed" and self.parent.is_capturing) or (self.mode == "freehand" and not self.parent.global_begin.isNull() and not self.parent.global_end.isNull()):
            begin_local = self.parent.global_begin - screen_geom.topLeft()
            end_local = self.parent.global_end - screen_geom.topLeft()
            rect = QRect(begin_local, end_local).normalized()

            if self.mode == "fixed":
                global_pos = QCursor.pos()
                local_x = global_pos.x() - screen_geom.x()
                local_y = global_pos.y() - screen_geom.y()
                rect = QRect(local_x - self.fixed_width // 2, local_y - self.fixed_height // 2, self.fixed_width, self.fixed_height)

            if rect.intersects(self.rect()):
                qp.fillRect(self.rect(), QColor(0, 0, 0, 30))
                qp.setPen(QPen(QColor(255, 0, 0), 2))
                qp.drawRect(rect)
                print(f"Drawing {'fixed' if self.mode == 'fixed' else 'freehand'} rect at: {rect.x()},{rect.y()} {rect.width()}x{rect.height()} on screen {screen_geom.x()},{screen_geom.y()}")

                width, height = rect.width(), rect.height()
                size_text = f"{width} × {height}"
                qp.setPen(QColor(255, 255, 0))
                text_x = rect.right() + 5 if rect.right() + 100 < self.width() else rect.left() - 100
                text_y = rect.bottom() + 20 if rect.bottom() + 30 < self.height() else rect.top() - 10
                text_rect = QRect(text_x - 2, text_y - 15, len(size_text) * 8 + 4, 20)
                qp.fillRect(text_rect, QColor(0, 0, 0, 180))
                qp.drawText(text_x, text_y, size_text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            global_pos = QCursor.pos()
            screen_geom = self.screen.geometry()
            if self.mode == "fixed":
                if hasattr(self, 'update_timer'):
                    self.update_timer.stop()
                local_x = global_pos.x() - screen_geom.x()
                local_y = global_pos.y() - screen_geom.y()
                print(f"Fixed mode click at global: {global_pos.x()},{global_pos.y()} local: {local_x},{local_y} on screen {screen_geom.x()},{screen_geom.y()}")
                rect = QRect(local_x - self.fixed_width // 2, local_y - self.fixed_height // 2, self.fixed_width, self.fixed_height)
                self.parent.global_begin = rect.topLeft() + screen_geom.topLeft()
                self.parent.global_end = rect.bottomRight() + screen_geom.topLeft()
                self.parent.finish_capture()
            else:
                if screen_geom.contains(global_pos):
                    self.parent.global_begin = global_pos
                    self.parent.global_end = global_pos
                    self.is_drawing = True
                    print(f"Freehand start at global: {global_pos.x()},{global_pos.y()} on screen {screen_geom.x()},{screen_geom.y()}")
                    self.parent.update_all_overlays()

    def mouseMoveEvent(self, event):
        if self.mode == "freehand" and self.is_drawing:
            self.parent.global_end = QCursor.pos()
            print(f"Freehand move to global: {self.parent.global_end.x()},{self.parent.global_end.y()} on screen {self.screen.geometry().x()},{self.screen.geometry().y()}")
            self.parent.update_all_overlays()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.mode == "freehand" and self.is_drawing:
            self.is_drawing = False
            self.parent.global_end = QCursor.pos()
            print(f"Freehand release at global: {self.parent.global_end.x()},{self.parent.global_end.y()} on screen {self.screen.geometry().x()},{self.screen.geometry().y()}")
            self.parent.finish_capture()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            for overlay in self.parent.overlays:
                overlay.close()
            self.parent.overlays = []
            self.parent.is_capturing = False
            self.parent.statusLabel.setText('Capture canceled')
            self.parent.show()

def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    print("Starting Screen Capture App...")
    try:
        screen_capture = ScreenCaptureApp()
        print("Application running. If you can't see the window, check for it in your taskbar.")
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error starting application: {e}")

if __name__ == '__main__':
    main()