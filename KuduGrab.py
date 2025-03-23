import sys
import os
import json
import traceback
import subprocess  # For opening folder
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QComboBox, QRadioButton, QFileDialog
from PyQt5.QtCore import Qt, QRect, QPoint, QTimer
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QScreen, QCursor, QImage, QIcon

# Version number
APP_VERSION = "v1.0.2"

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
                save_location = config.get("save_location", os.getcwd())
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
            self.last_capture_begin = None
            self.last_capture_end = None
            self.show_last_frame = False
            self.setWindowIcon(QIcon('icon.png'))
            self.setGeometry(300, 300, 300, 150)
            self.is_capturing = False
            self.capture_mode = None
            self.global_begin = QPoint()
            self.global_end = QPoint()
            self.output_mode = "clipboard"
            self.sizes, self.default_w, self.default_h, self.save_location = load_config()
            self.overlays = []  # Initialize overlays list
            self.screenshots = {}  # Initialize screenshots dict
            # Store last successful capture
            self.last_capture_pixmap = None
            # Add a flag to prevent concurrent operations
            self.is_overlay_operation_in_progress = False
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
            rapidLayout = QHBoxLayout()
            buttonLayout = QHBoxLayout()
            fixedSizeLayout = QHBoxLayout()
            locationLayout = QHBoxLayout()

            # Mode selection
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

            # Rapid Re Capture and Toggle Button
            self.rapidCaptureBtn = QPushButton('Rapid Re Capture', self)
            self.rapidCaptureBtn.clicked.connect(self.start_rapid_capture)
            self.rapidCaptureBtn.setFixedHeight(20)
            self.rapidCaptureBtn.setFixedWidth(120)
            self.rapidCaptureBtn.setStyleSheet("font-size: 10px; font-weight: bold;")
            self.rapidCaptureBtn.setEnabled(False)
            rapidLayout.addWidget(self.rapidCaptureBtn)

            self.toggleFrameBtn = QPushButton('□', self)
            self.toggleFrameBtn.setFixedSize(20, 20)
            self.toggleFrameBtn.clicked.connect(self.toggle_last_frame)
            self.toggleFrameBtn.setStyleSheet("font-size: 12px;")
            self.toggleFrameBtn.setEnabled(False)
            rapidLayout.addWidget(self.toggleFrameBtn)
            rapidLayout.addStretch(1)

            # Free Hand Capture and MP/Ratio
            self.captureBtn = QPushButton('Free Hand Capture', self)
            self.captureBtn.clicked.connect(self.start_freehand_capture)
            self.captureBtn.setFixedHeight(20)
            self.captureBtn.setFixedWidth(120)
            self.captureBtn.setStyleSheet("font-size: 10px; font-weight: bold;")
            buttonLayout.addWidget(self.captureBtn)
            buttonLayout.addStretch(1)

            infoLayout = QHBoxLayout()
            self.mpLabel = QLabel(self)
            self.ratioLabel = QLabel(self)
            infoLayout.addWidget(self.mpLabel)
            infoLayout.addWidget(self.ratioLabel)
            buttonLayout.addLayout(infoLayout)
            buttonLayout.addStretch(1)

            # Fixed Size Capture and W/H selection
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
            fixedSizeLayout.addWidget(self.heightInput)
            fixedSizeLayout.addWidget(heightLabel)
            fixedSizeLayout.addStretch(1)

            # Location selection with folder buttons
            self.locationLabel = QLabel(f"📁 {self.save_location}", self)
            self.locationLabel.setStyleSheet("font-size: 9px;")
            
            self.setLocationButton = QPushButton('📁 set', self)
            self.setLocationButton.clicked.connect(self.set_save_location)
            self.setLocationButton.setFixedHeight(22)
            self.setLocationButton.setFixedWidth(50)
            self.setLocationButton.setStyleSheet("font-size: 9px;")
            
            self.getLocationButton = QPushButton('📁 get', self)
            self.getLocationButton.clicked.connect(self.open_save_location)
            self.getLocationButton.setFixedHeight(22)
            self.getLocationButton.setFixedWidth(50)
            self.getLocationButton.setStyleSheet("font-size: 9px;")
            
            locationLayout.addWidget(self.locationLabel)
            locationLayout.addWidget(self.setLocationButton)
            locationLayout.addWidget(self.getLocationButton)
            locationLayout.addStretch(1)

            mainLayout.addLayout(modeLayout)
            mainLayout.addLayout(rapidLayout)
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

    def start_rapid_capture(self):
        try:
            # Check if we're already in an overlay operation
            if self.is_overlay_operation_in_progress:
                print("Overlay operation already in progress, ignoring request")
                return
                
            print("Starting rapid re-capture process...")
            if self.last_capture_begin is None or self.last_capture_end is None:
                print("No previous capture exists")
                return
                
            # Set the begin and end points directly from the last capture
            self.global_begin = QPoint(self.last_capture_begin)
            self.global_end = QPoint(self.last_capture_end)
            
            # Instead of creating overlays, directly perform the capture
            # This avoids disturbing the existing blue rectangle overlay
            self.capture_from_coordinates(self.global_begin, self.global_end)
            
        except Exception as e:
            print(f"Error in start_rapid_capture: {e}")
            traceback.print_exc()

    def capture_from_coordinates(self, begin_point, end_point):
        """Captures the screen area defined by the coordinates without creating overlays"""
        try:
            print("Direct capture from coordinates")
            
            # Get normalized capture dimensions
            x1 = min(begin_point.x(), end_point.x())
            y1 = min(begin_point.y(), end_point.y())
            x2 = max(begin_point.x(), end_point.x())
            y2 = max(begin_point.y(), end_point.y())
            
            width = x2 - x1
            height = y2 - y1
            
            print(f"Capturing from global: ({x1},{y1}) to ({x2},{y2}), size: {width}x{height}")
            
            # Check if we have a valid selection
            if width > 10 and height > 10:
                # Create pixmap for the selection
                selection = QPixmap(width, height)
                selection.fill(Qt.transparent)
                
                painter = QPainter(selection)
                selection_rect = QRect(x1, y1, width, height)
                
                # Take screenshots directly instead of using stored ones
                screenshots = {}
                screens = QApplication.screens()
                for i, screen in enumerate(screens):
                    geom = screen.geometry()
                    screen_pixmap = screen.grabWindow(0)
                    screenshots[i] = {
                        'geometry': geom,
                        'pixmap': screen_pixmap
                    }
                
                # Composite the relevant parts from each screen
                for i, screen_data in screenshots.items():
                    try:
                        geom = screen_data['geometry']
                        pixmap = screen_data['pixmap']
                        
                        if not pixmap or pixmap.isNull():
                            print(f"Warning: Invalid pixmap for screen {i}")
                            continue
                            
                        # Calculate intersection with this screen
                        overlap = selection_rect.intersected(geom)
                        if not overlap.isEmpty():
                            src_x = overlap.x() - geom.x()
                            src_y = overlap.y() - geom.y()
                            dst_x = overlap.x() - x1
                            dst_y = overlap.y() - y1
                            
                            # Double-check valid source coordinates
                            if (src_x >= 0 and src_y >= 0 and 
                                src_x + overlap.width() <= pixmap.width() and 
                                src_y + overlap.height() <= pixmap.height()):
                                painter.drawPixmap(dst_x, dst_y, pixmap, src_x, src_y, overlap.width(), overlap.height())
                            else:
                                print(f"Warning: Source coordinates out of bounds for screen {i}")
                    except Exception as e:
                        print(f"Error compositing screen {i}: {e}")
                        traceback.print_exc()
                            
                painter.end()
                
                # Process according to output mode
                if self.output_mode == "clipboard":
                    image = selection.toImage()
                    QApplication.clipboard().setImage(image)
                    print("Image copied to clipboard")
                elif self.output_mode == "fixed_location":
                    filename = f"capture_{x1}_{y1}_{width}x{height}.png"
                    filepath = os.path.join(self.save_location, filename)
                    counter = 1
                    while os.path.exists(filepath):
                        filename = f"capture_{x1}_{y1}_{width}x{height}_{counter}.png"
                        filepath = os.path.join(self.save_location, filename)
                        counter += 1
                    success = selection.save(filepath, "PNG")
                    print(f"Image saved to {filepath}: {success}")
                else:  # new_location
                    filepath, _ = QFileDialog.getSaveFileName(
                        self, 
                        "Save Capture", 
                        os.path.join(self.save_location, f"capture_{x1}_{y1}_{width}x{height}.png"), 
                        "PNG Files (*.png)"
                    )
                    if filepath:
                        success = selection.save(filepath, "PNG")
                        print(f"Image saved to user-selected path: {success}")
                        
                print("Direct capture completed successfully")
            else:
                print(f"Selection too small ({width}x{height}), not capturing")
                
        except Exception as e:
            print(f"Error in capture_from_coordinates: {e}")
            traceback.print_exc()

    def start_fixed_capture(self):
        try:
            # Check if we're already in an overlay operation
            if self.is_overlay_operation_in_progress:
                print("Overlay operation already in progress, ignoring request")
                return
                
            print("Starting fixed-size capture process...")
            width = int(self.widthInput.currentText())
            height = int(self.heightInput.currentText())
            self.default_w = width
            self.default_h = height
            save_config(self.sizes, self.default_w, self.default_h, self.save_location)
            self.capture_mode = "fixed"
            self.hide()
            
            self.is_overlay_operation_in_progress = True
            QApplication.processEvents()
            QTimer.singleShot(200, lambda: self._create_overlays(width=width, height=height))
        except Exception as e:
            self.is_overlay_operation_in_progress = False
            print(f"Error in start_fixed_capture: {e}")
            traceback.print_exc()
            self.show()

    def start_freehand_capture(self):
        try:
            # Check if we're already in an overlay operation
            if self.is_overlay_operation_in_progress:
                print("Overlay operation already in progress, ignoring request")
                return
                
            print("Starting free-hand capture process...")
            self.capture_mode = "freehand"
            self.hide()
            
            self.is_overlay_operation_in_progress = True
            QApplication.processEvents()
            QTimer.singleShot(200, self._create_overlays)
        except Exception as e:
            self.is_overlay_operation_in_progress = False
            print(f"Error in start_freehand_capture: {e}")
            traceback.print_exc()
            self.show()

    def toggle_last_frame(self):
        try:
            # Check if we have valid capture coordinates
            if not self.last_capture_begin or not self.last_capture_end:
                print("No previous capture exists to toggle")
                return
                
            # Update toggle state
            self.show_last_frame = not self.show_last_frame
            self.toggleFrameBtn.setText('■' if self.show_last_frame else '□')
            
            # Update button states
            self.rapidCaptureBtn.setEnabled(self.show_last_frame)
            self.captureBtn.setEnabled(not self.show_last_frame)
            self.fixedCaptureBtn.setEnabled(not self.show_last_frame)
            
            # Clean up any existing overlays
            for overlay in self.overlays:
                if overlay and hasattr(overlay, 'close'):
                    overlay.close()
            self.overlays = []
            
            # If toggling on, create a new overlay just for the blue rectangle
            if self.show_last_frame:
                screens = QApplication.screens()
                for screen in screens:
                    try:
                        screen_geom = screen.geometry()
                        
                        # Create a very simple overlay
                        overlay = SimpleRectangleOverlay(
                            self,
                            screen,
                            self.last_capture_begin,
                            self.last_capture_end
                        )
                        
                        self.overlays.append(overlay)
                        overlay.show()
                    except Exception as e:
                        print(f"Error creating overlay for screen: {e}")
            
        except Exception as e:
            print(f"Error in toggle_last_frame: {e}")
            traceback.print_exc()
            
            # If anything goes wrong, make sure to reset the state
            self.show_last_frame = False
            self.toggleFrameBtn.setText('□')
            self.rapidCaptureBtn.setEnabled(False)
            self.captureBtn.setEnabled(True)
            self.fixedCaptureBtn.setEnabled(True)
            
            # Ensure main window is visible
            self.show()

    def _cleanup_overlays(self):
        """Safely clean up all overlay widgets"""
        try:
            print(f"Cleaning up overlays. Count: {len(self.overlays) if hasattr(self, 'overlays') else 0}")
            
            if hasattr(self, 'overlays'):
                # Make a copy of the list since we're modifying it
                overlays_to_close = list(self.overlays)
                for overlay in overlays_to_close:
                    try:
                        if overlay and isinstance(overlay, QWidget):
                            print(f"Closing overlay at {overlay.pos()}")
                            # Hide first to prevent visual artifacts
                            overlay.hide()
                            # Then properly close
                            overlay.close()
                            # Force Qt to process the close event
                            QApplication.processEvents()
                    except Exception as e:
                        print(f"Error closing overlay: {e}")
                        traceback.print_exc()
                        
            # Clear the list
            self.overlays = []
            
            # Always clear screenshots to avoid memory leaks
            self.screenshots = {}
                
            # Reset capture state if needed
            if self.is_capturing and self.capture_mode != "rapid":
                self.is_capturing = False
                
            print("Overlay cleanup completed")
            
        except Exception as e:
            print(f"Error in _cleanup_overlays: {e}")
            traceback.print_exc()

    def _create_overlays(self, width=800, height=600):
        try:
            # Clean up any existing overlays
            self._cleanup_overlays()
            
            # Reset collections
            self.overlays = []
            self.screenshots = {}
            
            # Create overlays for each screen
            screens = QApplication.screens()
            for i, screen in enumerate(screens):
                # Create the overlay
                overlay = OverlayWidget(self, screen, mode=self.capture_mode, fixed_width=width, fixed_height=height)
                self.overlays.append(overlay)
                
                # Take screenshot
                screen_pixmap = screen.grabWindow(0)
                self.screenshots[i] = {
                    'geometry': screen.geometry(),
                    'pixmap': screen_pixmap
                }
                
                # Show overlay after we've prepared its data
                overlay.show()
                overlay.update()
                
                print(f"Overlay {i} created for capture at {screen.geometry().x()},{screen.geometry().y()} {screen.geometry().width()}x{screen.geometry().height()}")
                
            self.is_capturing = True
            
            # For rapid mode, immediately finish the capture
            if self.capture_mode == "rapid":
                QTimer.singleShot(200, self.finish_capture)
        except Exception as e:
            self.is_overlay_operation_in_progress = False
            print(f"Error creating overlays: {e}")
            traceback.print_exc()
            self.show()

    def update_all_overlays(self):
        try:
            for overlay in self.overlays:
                if overlay and overlay.isVisible():
                    overlay.update()
        except Exception as e:
            print(f"Error in update_all_overlays: {e}")
            traceback.print_exc()

    def finish_capture(self):
        try:
            print("Starting finish_capture")
            
            # Store last capture coordinates - make explicit copies
            if self.global_begin.isNull() or self.global_end.isNull():
                print("Error: global_begin or global_end is null!")
                self.is_overlay_operation_in_progress = False
                self._cleanup_overlays()
                self.show()
                return
                
            self.last_capture_begin = QPoint(self.global_begin)
            self.last_capture_end = QPoint(self.global_end)
            
            # Get normalized capture dimensions
            x1 = min(self.global_begin.x(), self.global_end.x())
            y1 = min(self.global_begin.y(), self.global_end.y())
            x2 = max(self.global_begin.x(), self.global_end.x())
            y2 = max(self.global_begin.y(), self.global_end.y())
            
            # Fix potential issues with global end coordinate
            if self.global_end.y() < self.global_begin.y():
                # Fix the common mistake in the original code where y2 used wrong coordinate
                y2 = self.global_end.y()
            
            width = x2 - x1
            height = y2 - y1
            
            print(f"Capturing from global: ({x1},{y1}) to ({x2},{y2}), size: {width}x{height}")
            
            # Check if we have a valid selection
            if width > 10 and height > 10:
                try:
                    # Create pixmap for the selection
                    selection = QPixmap(width, height)
                    # Fill with transparent background first (in case portions are outside screens)
                    selection.fill(Qt.transparent)
                    
                    painter = QPainter(selection)
                    selection_rect = QRect(x1, y1, width, height)
                    
                    # Composite the relevant parts from each screen
                    screen_count = len(self.screenshots)
                    print(f"Compositing from {screen_count} screens")
                    
                    for i, screen_data in self.screenshots.items():
                        try:
                            geom = screen_data['geometry']
                            pixmap = screen_data['pixmap']
                            
                            if not pixmap or pixmap.isNull():
                                print(f"Warning: Invalid pixmap for screen {i}")
                                continue
                                
                            # Calculate intersection with this screen
                            overlap = selection_rect.intersected(geom)
                            if not overlap.isEmpty():
                                src_x = overlap.x() - geom.x()
                                src_y = overlap.y() - geom.y()
                                dst_x = overlap.x() - x1
                                dst_y = overlap.y() - y1
                                
                                print(f"Screen {i}: Overlap at {overlap.x()},{overlap.y()} size {overlap.width()}x{overlap.height()}")
                                print(f"  Source coords: {src_x},{src_y}")
                                print(f"  Dest coords: {dst_x},{dst_y}")
                                
                                # Double-check valid source coordinates
                                if (src_x >= 0 and src_y >= 0 and 
                                    src_x + overlap.width() <= pixmap.width() and 
                                    src_y + overlap.height() <= pixmap.height()):
                                    painter.drawPixmap(dst_x, dst_y, pixmap, src_x, src_y, overlap.width(), overlap.height())
                                else:
                                    print(f"Warning: Source coordinates out of bounds for screen {i}")
                        except Exception as e:
                            print(f"Error compositing screen {i}: {e}")
                            traceback.print_exc()
                                
                    painter.end()
                    
                    # Store a copy of the successful capture
                    self.last_capture_pixmap = QPixmap(selection)
                    
                    # Process according to output mode
                    if self.output_mode == "clipboard":
                        image = selection.toImage()
                        QApplication.clipboard().setImage(image)
                        print("Image copied to clipboard")
                    elif self.output_mode == "fixed_location":
                        filename = f"capture_{x1}_{y1}_{width}x{height}.png"
                        filepath = os.path.join(self.save_location, filename)
                        counter = 1
                        while os.path.exists(filepath):
                            filename = f"capture_{x1}_{y1}_{width}x{height}_{counter}.png"
                            filepath = os.path.join(self.save_location, filename)
                            counter += 1
                        success = selection.save(filepath, "PNG")
                        print(f"Image saved to {filepath}: {success}")
                    else:  # new_location
                        filepath, _ = QFileDialog.getSaveFileName(
                            self, 
                            "Save Capture", 
                            os.path.join(self.save_location, f"capture_{x1}_{y1}_{width}x{height}.png"), 
                            "PNG Files (*.png)"
                        )
                        if filepath:
                            success = selection.save(filepath, "PNG")
                            print(f"Image saved to user-selected path: {success}")
                except Exception as e:
                    print(f"Error processing capture: {e}")
                    traceback.print_exc()
            else:
                print(f"Selection too small ({width}x{height}), not capturing")
            
            # Clean up overlays
            self._cleanup_overlays()
            
            # Reset state
            self.is_capturing = False
            self.global_begin = QPoint()
            self.global_end = QPoint()
            
            # Enable toggle button since we now have a valid capture
            self.toggleFrameBtn.setEnabled(True)
            
            # Mark operation as complete
            self.is_overlay_operation_in_progress = False
            
            # Restore main window
            print("Showing main window")
            QApplication.processEvents()
            self.show()
            QApplication.processEvents()
            
            print("Finish capture completed")
            
        except Exception as e:
            self.is_overlay_operation_in_progress = False
            print(f"Error in finish_capture: {e}")
            traceback.print_exc()
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
                save_config(self.sizes, self.default_w, self.default_h, self.save_location)
                print(f"Save location set to: {self.save_location}")
        except Exception as e:
            print(f"Error in set_save_location: {e}")

    def open_save_location(self):
        try:
            if os.path.exists(self.save_location):
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

class SimpleRectangleOverlay(QWidget):
    """A very simple overlay widget that just shows a blue rectangle."""
    def __init__(self, parent, screen, begin_point, end_point):
        super().__init__(None)  # Create without any initial flags
        
        self.parent = parent
        self.screen = screen
        self.screen_geom = screen.geometry()
        self.begin_point = begin_point
        self.end_point = end_point
        
        # Set widget properties
        self.setGeometry(self.screen_geom)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Use ToolTip flag to hide from taskbar and remove window decorations
        self.setWindowFlags(Qt.FramelessWindowHint | 
                            Qt.WindowStaysOnTopHint | 
                            Qt.Tool |  # Tool windows don't show in taskbar
                            Qt.ToolTip)  # Hides form icon and won't steal focus
        
    def paintEvent(self, event):
        """Just draw a blue rectangle and nothing else."""
        try:
            qp = QPainter(self)
            
            # Convert global points to local for this screen
            begin_local = self.begin_point - self.screen_geom.topLeft()
            end_local = self.end_point - self.screen_geom.topLeft()
            
            # Create normalized rect (ensuring width/height are positive)
            rect = QRect(
                min(begin_local.x(), end_local.x()),
                min(begin_local.y(), end_local.y()),
                abs(end_local.x() - begin_local.x()),
                abs(end_local.y() - begin_local.y())
            )
            
            # Only draw if this rect intersects this overlay
            if rect.intersects(self.rect()):
                # Semi-transparent background
                qp.fillRect(self.rect(), QColor(0, 0, 0, 30))
                
                # Blue dashed rectangle 
                blue_pen = QPen(QColor(0, 0, 255), 2, Qt.DashLine)
                qp.setPen(blue_pen)
                qp.drawRect(rect)
                
                # Size info
                width, height = rect.width(), rect.height()
                size_text = f"{width} × {height}"
                qp.setPen(QColor(255, 255, 0))
                
                # Position text
                text_x = rect.right() + 5 if rect.right() + 100 < self.width() else rect.left() - 100
                text_y = rect.bottom() + 20 if rect.bottom() + 30 < self.height() else rect.top() - 10
                
                # Ensure text coordinates are valid
                text_x = max(0, min(text_x, self.width() - 100))
                text_y = max(15, min(text_y, self.height() - 5))
                
                # Draw text with background
                text_rect = QRect(text_x - 2, text_y - 15, len(size_text) * 8 + 4, 20)
                qp.fillRect(text_rect, QColor(0, 0, 0, 180))
                qp.drawText(text_x, text_y, size_text)
                
        except Exception as e:
            print(f"Error in SimpleRectangleOverlay.paintEvent: {e}")
            
    def keyPressEvent(self, event):
        """Handle Escape key to exit the overlay."""
        if event.key() == Qt.Key_Escape:
            self.parent.toggle_last_frame()  


class OverlayWidget(QWidget):
    def __init__(self, parent, screen, mode="freehand", fixed_width=800, fixed_height=600):
        super().__init__(None)  # Create without any initial flags
        try:
            self.parent = parent
            self.screen = screen
            self.is_drawing = False
            self.mode = mode
            self.fixed_width = fixed_width
            self.fixed_height = fixed_height
            self.handle_size = 10
            self.selected_handle = None
            
            # Store an explicit reference to screen geometry
            self.screen_geometry = screen.geometry()
            geom = self.screen_geometry
            
            # Set this widget's geometry to match the screen
            self.setGeometry(geom)
            print(f"Overlay widget geometry: {geom.x()},{geom.y()} {geom.width()}x{geom.height()}")
            
            # Set basic properties
            self.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
            if mode in ["freehand", "fixed"]:
                self.setCursor(Qt.CrossCursor)
            self.setMouseTracking(True)
            self.setAttribute(Qt.WA_TranslucentBackground)
            
            # Set window flags that prevent flickering and ensure it stays on top
            self.setWindowFlags(Qt.FramelessWindowHint | 
                                Qt.WindowStaysOnTopHint | 
                                Qt.Tool |  # Tool windows don't show in taskbar
                                Qt.ToolTip |  # Hides form icon
                                Qt.NoDropShadowWindowHint)  # Prevents shadow artifacts

            # Add instructions label for active capture modes
            if mode in ["freehand", "fixed"]:
                instruction_text = (
                    "Click and drag to select an area, then release to capture" if mode == "freehand" 
                    else f"Click to place a {fixed_width}×{fixed_height} capture area"
                )
                self.instructions = QLabel(instruction_text, self)
                self.instructions.setAlignment(Qt.AlignCenter)
                self.instructions.setStyleSheet(
                    "background-color: rgba(0, 0, 0, 180); color: white; padding: 10px; border-radius: 5px; font-size: 14px;"
                )
                self.instructions.adjustSize()
                self.instructions.move((geom.width() - self.instructions.width()) // 2, 20)

            # For fixed size capture, we need to update the view frequently to show cursor position
            if mode == "fixed":
                self.update_timer = QTimer(self)
                self.update_timer.timeout.connect(self.update)
                self.update_timer.start(50)
                
            # Make sure to call update after setup is complete
            self.update()
        except Exception as e:
            print(f"Error in OverlayWidget __init__: {e}")
            traceback.print_exc()

    def paintEvent(self, event):
        try:
            qp = QPainter(self)
            qp.setClipRect(self.rect())
            
            screen_geom = self.screen.geometry()
            
            # Get screenshot for this screen - defensive lookups
            screenshot_data = self.parent.screenshots.get(self.parent.overlays.index(self) if self in self.parent.overlays else -1, None)
            screenshot = screenshot_data.get('pixmap', None) if screenshot_data else None
            
            if screenshot and not screenshot.isNull():
                qp.drawPixmap(0, 0, screenshot)
            else:
                # If no valid screenshot, draw a semi-transparent background as fallback
                qp.fillRect(self.rect(), QColor(0, 0, 0, 10))

            # Only handle active capture operations (fixed size or freehand)
            # REMOVED the last frame overlay code since that's now handled by SimpleRectangleOverlay

            # Red frame for active capture operations
            if self.mode == "fixed" and self.parent.is_capturing:
                global_pos = QCursor.pos()
                local_x = global_pos.x() - screen_geom.x()
                local_y = global_pos.y() - screen_geom.y()
                
                # Create a rect with the fixed dimensions centered on cursor
                rect = QRect(
                    local_x - self.fixed_width // 2, 
                    local_y - self.fixed_height // 2, 
                    self.fixed_width, 
                    self.fixed_height
                )

                # Only draw if this rect intersects this overlay
                if rect.intersects(self.rect()):
                    # Draw semi-transparent overlay
                    qp.fillRect(self.rect(), QColor(0, 0, 0, 30))
                    
                    # Draw red frame
                    qp.setPen(QPen(QColor(255, 0, 0), 2))
                    qp.drawRect(rect)
                    
                    # Draw size info
                    width, height = rect.width(), rect.height()
                    size_text = f"{width} × {height}"
                    qp.setPen(QColor(255, 255, 0))
                    
                    # Position text in a visible area
                    text_x = rect.right() + 5 if rect.right() + 100 < self.width() else rect.left() - 100
                    text_y = rect.bottom() + 20 if rect.bottom() + 30 < self.height() else rect.top() - 10
                    
                    # Ensure text coordinates are valid
                    text_x = max(0, min(text_x, self.width() - 100))
                    text_y = max(15, min(text_y, self.height() - 5))
                    
                    # Draw background for text
                    text_rect = QRect(text_x - 2, text_y - 15, len(size_text) * 8 + 4, 20)
                    qp.fillRect(text_rect, QColor(0, 0, 0, 180))
                    qp.drawText(text_x, text_y, size_text)

            elif self.mode == "freehand" and self.parent.is_capturing and not self.parent.global_begin.isNull() and not self.parent.global_end.isNull():
                # Check if both points are valid
                if self.parent.global_begin.x() < -10000 or self.parent.global_begin.y() < -10000 or \
                self.parent.global_end.x() < -10000 or self.parent.global_end.y() < -10000:
                    print("Invalid coordinates for freehand selection")
                    return
                    
                # Convert global points to local for this screen
                begin_local = self.parent.global_begin - screen_geom.topLeft()
                end_local = self.parent.global_end - screen_geom.topLeft()
                
                # Create normalized rect
                rect = QRect(
                    min(begin_local.x(), end_local.x()),
                    min(begin_local.y(), end_local.y()),
                    abs(end_local.x() - begin_local.x()),
                    abs(end_local.y() - begin_local.y())
                )

                # Only draw if this rect intersects this overlay
                if rect.intersects(self.rect()):
                    # Draw semi-transparent overlay
                    qp.fillRect(self.rect(), QColor(0, 0, 0, 30))
                    
                    # Draw red frame
                    qp.setPen(QPen(QColor(255, 0, 0), 2))
                    qp.drawRect(rect)
                    
                    # Draw size info
                    width, height = rect.width(), rect.height()
                    size_text = f"{width} × {height}"
                    qp.setPen(QColor(255, 255, 0))
                    
                    # Position text in a visible area
                    text_x = rect.right() + 5 if rect.right() + 100 < self.width() else rect.left() - 100
                    text_y = rect.bottom() + 20 if rect.bottom() + 30 < self.height() else rect.top() - 10
                    
                    # Ensure text coordinates are valid
                    text_x = max(0, min(text_x, self.width() - 100))
                    text_y = max(15, min(text_y, self.height() - 5))
                    
                    # Draw background for text
                    text_rect = QRect(text_x - 2, text_y - 15, len(size_text) * 8 + 4, 20)
                    qp.fillRect(text_rect, QColor(0, 0, 0, 180))
                    qp.drawText(text_x, text_y, size_text)

        except Exception as e:
            print(f"Error in paintEvent: {e}")
            traceback.print_exc()

    def mousePressEvent(self, event):
        try:
            if event.button() == Qt.LeftButton and self.parent.is_capturing:
                global_pos = QCursor.pos()
                screen_geom = self.screen.geometry()
                local_pos = global_pos - screen_geom.topLeft()
                print(f"Mouse press in mode: {self.mode} at global: {global_pos.x()},{global_pos.y()}")

                if self.mode == "fixed":
                    # Stop the update timer if it exists
                    if hasattr(self, 'update_timer') and self.update_timer.isActive():
                        self.update_timer.stop()
                        
                    # Calculate position
                    local_x = global_pos.x() - screen_geom.x()
                    local_y = global_pos.y() - screen_geom.y()
                    print(f"Fixed mode click at global: {global_pos.x()},{global_pos.y()} local: {local_x},{local_y} on screen {screen_geom.x()},{screen_geom.y()}")
                    
                    # Create rect centered on click position
                    rect = QRect(
                        local_x - self.fixed_width // 2, 
                        local_y - self.fixed_height // 2, 
                        self.fixed_width, 
                        self.fixed_height
                    )
                    
                    # Convert to global coordinates
                    self.parent.global_begin = rect.topLeft() + screen_geom.topLeft()
                    self.parent.global_end = rect.bottomRight() + screen_geom.topLeft()
                    
                    # Finish capture
                    self.parent.finish_capture()
                    
                elif self.mode == "freehand" and screen_geom.contains(global_pos):
                    # Start drag operation
                    self.parent.global_begin = global_pos
                    self.parent.global_end = global_pos
                    self.is_drawing = True
                    print(f"Freehand start at global: {global_pos.x()},{global_pos.y()} on screen {screen_geom.x()},{screen_geom.y()}")
                    self.parent.update_all_overlays()
        except Exception as e:
            print(f"Error in mousePressEvent: {e}")
            traceback.print_exc()

    def mouseMoveEvent(self, event):
        try:
            if self.parent.is_capturing:
                global_pos = QCursor.pos()
                screen_geom = self.screen.geometry()
                
                # Check for valid cursor position
                if global_pos.x() < -10000 or global_pos.y() < -10000:
                    return
                    
                local_pos = global_pos - screen_geom.topLeft()

                if self.mode == "freehand" and self.is_drawing:
                    # Update end position and redraw all overlays
                    self.parent.global_end = global_pos
                    print(f"Freehand move to global: {self.parent.global_end.x()},{self.parent.global_end.y()} on screen {self.screen.geometry().x()},{self.screen.geometry().y()}")
                    self.parent.update_all_overlays()
                elif self.mode == "fixed":
                    # Just update this overlay to show preview rectangle
                    self.update()
        except Exception as e:
            print(f"Error in mouseMoveEvent: {e}")
            traceback.print_exc()

    def mouseReleaseEvent(self, event):
        try:
            if event.button() == Qt.LeftButton and self.parent.is_capturing:
                global_pos = QCursor.pos()
                
                # Check for valid cursor position
                if global_pos.x() < -10000 or global_pos.y() < -10000:
                    print("Invalid cursor position in mouseReleaseEvent")
                    return
                    
                if self.mode == "freehand" and self.is_drawing:
                    self.is_drawing = False
                    self.parent.global_end = global_pos
                    print(f"Freehand release at global: {self.parent.global_end.x()},{self.parent.global_end.y()} on screen {self.screen.geometry().x()},{self.screen.geometry().y()}")
                    
                    # Check if we have a minimum size selection
                    width = abs(self.parent.global_end.x() - self.parent.global_begin.x())
                    height = abs(self.parent.global_end.y() - self.parent.global_begin.y())
                    
                    if width < 10 or height < 10:
                        print(f"Selection too small ({width}x{height}), aborting capture")
                        self.parent.is_overlay_operation_in_progress = False
                        self.parent._cleanup_overlays()
                        self.parent.show()
                        return
                        
                    self.parent.finish_capture()
        except Exception as e:
            print(f"Error in mouseReleaseEvent: {e}")
            traceback.print_exc()
            self.parent.is_overlay_operation_in_progress = False
            self.parent.show()

    def keyPressEvent(self, event):
        try:
            if event.key() == Qt.Key_Escape and self.parent.is_capturing:
                # Stop any active timers
                if hasattr(self, 'update_timer') and self.update_timer.isActive():
                    self.update_timer.stop()
                    
                # Clean up and abort
                self.parent._cleanup_overlays()
                self.parent.is_capturing = False
                self.parent.is_overlay_operation_in_progress = False
                self.parent.show()
        except Exception as e:
            print(f"Error in keyPressEvent: {e}")
            traceback.print_exc()
            self.parent.is_overlay_operation_in_progress = False
            self.parent.show()

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