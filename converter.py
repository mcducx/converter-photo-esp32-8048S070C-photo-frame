import os
import sys
import traceback
from PIL import Image
import argparse
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# =============================================
# ADDITIONAL FORMATS SUPPORT
# =============================================

# HEIF/HEIC support (iPhone formats)
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HAS_HEIF = True
except ImportError:
    HAS_HEIF = False
except Exception:
    HAS_HEIF = False

# RAW file support (CR2, NEF, etc.)
try:
    import rawpy

    HAS_RAW = True
except ImportError:
    HAS_RAW = False


def get_supported_formats():
    """Returns a list of supported formats"""
    base_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp', '.gif')
    heif_formats = ()
    raw_formats = ()

    if HAS_HEIF:
        heif_formats = ('.heif', '.heic', '.hif')

    if HAS_RAW:
        raw_formats = ('.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.orf', '.rw2')

    return base_formats + heif_formats + raw_formats


class ImageProcessor(QThread):
    """Thread for processing images in background"""
    progress = pyqtSignal(int)
    log_message = pyqtSignal(str)
    processing_file = pyqtSignal(str)
    finished_success = pyqtSignal(int, int, int)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.input_dir = ""
        self.output_dir = ""
        self.target_size = (480, 800)
        self.jpeg_quality = 95
        self.background_color = (0, 0, 0)  # BLACK
        self.crop_mode = False
        self.overwrite = False
        self.running = True

    def stop(self):
        self.running = False

    def process_raw_image(self, input_path):
        """Processes a RAW file and returns a PIL Image"""
        try:
            with rawpy.imread(input_path) as raw:
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    half_size=False,
                    no_auto_bright=False,
                    output_bps=8,
                    output_color=rawpy.ColorSpace.sRGB,
                    gamma=(2.222, 4.5),
                    user_black=None,
                    user_sat=None,
                    no_auto_scale=False,
                    demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD
                )
            img = Image.fromarray(rgb)
            return img
        except Exception as e:
            raise Exception(f"RAW processing error: {e}")

    def process_image(self, input_path, output_path):
        """Processes a single image"""
        try:
            _, ext = os.path.splitext(input_path)
            ext_lower = ext.lower()

            if HAS_RAW and ext_lower in ('.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.orf', '.rw2'):
                img = self.process_raw_image(input_path)
            else:
                img = Image.open(input_path)

            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, self.background_color)
                if img.mode == 'P':
                    img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            if self.crop_mode:
                img.thumbnail((self.target_size[0] * 2, self.target_size[1] * 2), Image.Resampling.LANCZOS)
                left = max(0, (img.width - self.target_size[0]) // 2)
                top = max(0, (img.height - self.target_size[1]) // 2)
                right = min(img.width, left + self.target_size[0])
                bottom = min(img.height, top + self.target_size[1])
                img = img.crop((left, top, right, bottom))

                if img.size != self.target_size:
                    img = img.resize(self.target_size, Image.Resampling.LANCZOS)
                new_img = img
            else:
                img.thumbnail(self.target_size, Image.Resampling.LANCZOS)
                new_img = Image.new('RGB', self.target_size, self.background_color)
                offset = (
                    (self.target_size[0] - img.size[0]) // 2,
                    (self.target_size[1] - img.size[1]) // 2
                )
                new_img.paste(img, offset)

            new_img.save(output_path, 'JPEG', quality=self.jpeg_quality, optimize=True, progressive=False)
            return True

        except Exception as e:
            raise Exception(f"Image processing error: {e}")

    def run(self):
        try:
            if not os.path.exists(self.input_dir):
                self.error_occurred.emit(f"Input directory does not exist: {self.input_dir}")
                return

            os.makedirs(self.output_dir, exist_ok=True)

            supported_formats = get_supported_formats()
            files = os.listdir(self.input_dir)
            image_files = []

            for filename in files:
                _, ext = os.path.splitext(filename)
                if ext.lower() in supported_formats:
                    image_files.append(filename)

            if not image_files:
                self.error_occurred.emit(f"No supported images found in: {self.input_dir}")
                return

            total = len(image_files)
            processed = 0
            skipped = 0
            failed = 0

            for i, filename in enumerate(image_files):
                if not self.running:
                    break

                self.processing_file.emit(filename)

                input_path = os.path.join(self.input_dir, filename)
                name_without_ext = os.path.splitext(filename)[0]
                output_filename = f"{name_without_ext}.jpg"
                output_path = os.path.join(self.output_dir, output_filename)

                if os.path.exists(output_path) and not self.overwrite:
                    self.log_message.emit(f"Skipped (exists): {filename}")
                    skipped += 1
                else:
                    try:
                        if self.process_image(input_path, output_path):
                            processed += 1
                            self.log_message.emit(f"Processed: {filename}")
                        else:
                            failed += 1
                            self.log_message.emit(f"Failed: {filename}")
                    except Exception as e:
                        failed += 1
                        self.log_message.emit(f"Error: {filename} - {str(e)}")

                progress = int((i + 1) / total * 100)
                self.progress.emit(progress)

            if self.running:
                self.finished_success.emit(processed, skipped, failed)

        except Exception as e:
            self.error_occurred.emit(f"Processing error: {str(e)}")


class SettingsDialog(QDialog):
    """Settings dialog window"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Settings")
        self.setFixedSize(400, 300)
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            QSpinBox, QComboBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton {
                background-color: #505050;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #606060;
            }
        """)

        layout = QVBoxLayout()

        # Target size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Target Size:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 2000)
        self.width_spin.setValue(self.parent.target_width)
        size_layout.addWidget(self.width_spin)
        size_layout.addWidget(QLabel("x"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 2000)
        self.height_spin.setValue(self.parent.target_height)
        size_layout.addWidget(self.height_spin)
        layout.addLayout(size_layout)

        # JPEG Quality
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("JPEG Quality:"))
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(self.parent.jpeg_quality)
        quality_layout.addWidget(self.quality_spin)
        quality_layout.addStretch()
        layout.addLayout(quality_layout)

        # Background Color
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Background Color:"))
        self.color_combo = QComboBox()
        self.color_combo.addItems(["Black", "White", "Gray", "Custom"])
        self.color_combo.currentTextChanged.connect(self.on_color_changed)
        color_layout.addWidget(self.color_combo)

        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(30, 30)
        self.color_btn.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_btn)
        layout.addLayout(color_layout)

        # Processing mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Default Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Fit with background", "Crop to fit"])
        self.mode_combo.setCurrentIndex(1 if self.parent.crop_mode else 0)
        mode_layout.addWidget(self.mode_combo)
        layout.addLayout(mode_layout)

        # Format support info
        info_label = QLabel(f"HEIF support: {'Yes' if HAS_HEIF else 'No'}\n"
                            f"RAW support: {'Yes' if HAS_RAW else 'No'}")
        info_label.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(info_label)

        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.update_color_button()

    def on_color_changed(self, text):
        self.update_color_button()

    def update_color_button(self):
        color_text = self.color_combo.currentText()
        if color_text == "Black":
            color = QColor(0, 0, 0)
        elif color_text == "White":
            color = QColor(255, 255, 255)
        elif color_text == "Gray":
            color = QColor(128, 128, 128)
        else:
            color = QColor(*self.parent.background_color)

        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({color.red()}, {color.green()}, {color.blue()});
                border: 2px solid #ffffff;
            }}
        """)

    def choose_color(self):
        current_color = QColor(*self.parent.background_color)
        color = QColorDialog.getColor(current_color, self, "Choose Background Color")
        if color.isValid():
            self.parent.background_color = (color.red(), color.green(), color.blue())
            self.color_combo.setCurrentText("Custom")
            self.update_color_button()

    def save_settings(self):
        self.parent.target_width = self.width_spin.value()
        self.parent.target_height = self.height_spin.value()
        self.parent.target_size = (self.parent.target_width, self.parent.target_height)
        self.parent.jpeg_quality = self.quality_spin.value()
        self.parent.crop_mode = self.mode_combo.currentIndex() == 1

        color_text = self.color_combo.currentText()
        if color_text == "Black":
            self.parent.background_color = (0, 0, 0)
        elif color_text == "White":
            self.parent.background_color = (255, 255, 255)
        elif color_text == "Gray":
            self.parent.background_color = (128, 128, 128)

        self.accept()


class ImageConverterUI(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.target_width = 480
        self.target_height = 800
        self.target_size = (480, 800)
        self.jpeg_quality = 95
        self.background_color = (0, 0, 0)
        self.crop_mode = False
        self.processor = None
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Image Converter Pro - Black Background")
        self.setGeometry(100, 100, 800, 700)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton {
                background-color: #404040;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:disabled {
                background-color: #2b2b2b;
                color: #666666;
            }
            QPushButton#start_btn {
                background-color: #0066cc;
            }
            QPushButton#start_btn:hover {
                background-color: #0077dd;
            }
            QPushButton#stop_btn {
                background-color: #cc3300;
            }
            QPushButton#stop_btn:hover {
                background-color: #dd4400;
            }
            QProgressBar {
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #0066cc;
                border-radius: 4px;
            }
            QTextEdit {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
            QCheckBox {
                color: #ffffff;
            }
            QGroupBox {
                color: #ffffff;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Header
        header_label = QLabel("🖼️ Image Converter Pro v3.0")
        header_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        header_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header_label)

        sub_label = QLabel("Convert images to JPEG with black background (800×480)")
        sub_label.setStyleSheet("font-size: 12px; color: #888888;")
        sub_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(sub_label)

        main_layout.addSpacing(20)

        # Input directory
        input_group = QGroupBox("Input Directory")
        input_layout = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Select input directory...")
        input_layout.addWidget(self.input_edit)

        input_btn = QPushButton("Browse...")
        input_btn.clicked.connect(self.browse_input)
        input_layout.addWidget(input_btn)
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        # Output directory
        output_group = QGroupBox("Output Directory")
        output_layout = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Select output directory...")
        output_layout.addWidget(self.output_edit)

        output_btn = QPushButton("Browse...")
        output_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(output_btn)
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)

        # Options
        options_group = QGroupBox("Processing Options")
        options_layout = QVBoxLayout()

        # Mode selection
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Processing Mode:"))
        self.fit_radio = QRadioButton("Fit with black background")
        self.fit_radio.setChecked(True)
        self.crop_radio = QRadioButton("Crop to fit")
        mode_layout.addWidget(self.fit_radio)
        mode_layout.addWidget(self.crop_radio)
        mode_layout.addStretch()
        options_layout.addLayout(mode_layout)

        # Options row
        options_row = QHBoxLayout()
        self.overwrite_check = QCheckBox("Overwrite existing files")
        options_row.addWidget(self.overwrite_check)
        options_row.addStretch()

        settings_btn = QPushButton("Settings ⚙️")
        settings_btn.clicked.connect(self.open_settings)
        settings_btn.setStyleSheet("padding: 5px 15px;")
        options_row.addWidget(settings_btn)
        options_layout.addLayout(options_row)

        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)

        # Control buttons
        control_layout = QHBoxLayout()

        self.start_btn = QPushButton("▶ Start Processing")
        self.start_btn.setObjectName("start_btn")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setMinimumHeight(40)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)

        self.preview_btn = QPushButton("👁 Preview")
        self.preview_btn.clicked.connect(self.show_preview)
        self.preview_btn.setMinimumHeight(40)

        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.preview_btn)
        main_layout.addLayout(control_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #888888; font-size: 11px;")
        main_layout.addWidget(self.status_label)

        # Current file label
        self.current_file_label = QLabel("")
        self.current_file_label.setStyleSheet("color: #66ccff; font-size: 12px; font-weight: bold;")
        main_layout.addWidget(self.current_file_label)

        # Log output
        log_group = QGroupBox("Processing Log")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        # Results label
        self.results_label = QLabel("")
        self.results_label.setStyleSheet("color: #ffffff; font-size: 12px;")
        main_layout.addWidget(self.results_label)

        # Set default paths (optional)
        if os.path.exists("/Users/mcducx/Downloads/input"):
            self.input_edit.setText("/Users/mcducx/Downloads/input")
        if os.path.exists("/Users/mcducx/Downloads/output"):
            self.output_edit.setText("/Users/mcducx/Downloads/output")

    def browse_input(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Input Directory")
        if directory:
            self.input_edit.setText(directory)

    def browse_output(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_edit.setText(directory)

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec_():
            self.log_message("Settings updated")

    def log_message(self, message):
        timestamp = QTime.currentTime().toString("HH:mm:ss")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def show_preview(self):
        input_dir = self.input_edit.text()
        if not input_dir or not os.path.exists(input_dir):
            QMessageBox.warning(self, "Warning", "Please select a valid input directory first!")
            return

        supported_formats = get_supported_formats()
        files = [f for f in os.listdir(input_dir)
                 if os.path.splitext(f)[1].lower() in supported_formats]

        if not files:
            QMessageBox.information(self, "Info", "No supported images found in input directory!")
            return

        # Show first image info
        first_file = files[0]
        input_path = os.path.join(input_dir, first_file)

        try:
            img = Image.open(input_path)
            info = (f"Preview: {first_file}\n"
                    f"Size: {img.width}×{img.height}\n"
                    f"Format: {img.format}\n"
                    f"Mode: {img.mode}\n"
                    f"Target size: {self.target_width}×{self.target_height}")

            QMessageBox.information(self, "Image Preview", info)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Cannot preview image: {str(e)}")

    def start_processing(self):
        input_dir = self.input_edit.text()
        output_dir = self.output_edit.text()

        if not input_dir or not os.path.exists(input_dir):
            QMessageBox.critical(self, "Error", "Please select a valid input directory!")
            return

        if not output_dir:
            QMessageBox.critical(self, "Error", "Please select an output directory!")
            return

        self.crop_mode = self.crop_radio.isChecked()
        overwrite = self.overwrite_check.isChecked()

        # Disable controls during processing
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.preview_btn.setEnabled(False)
        self.input_edit.setEnabled(False)
        self.output_edit.setEnabled(False)

        # Clear previous results
        self.log_text.clear()
        self.results_label.clear()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Processing...")

        # Start processor thread
        self.processor = ImageProcessor()
        self.processor.input_dir = input_dir
        self.processor.output_dir = output_dir
        self.processor.target_size = self.target_size
        self.processor.jpeg_quality = self.jpeg_quality
        self.processor.background_color = self.background_color
        self.processor.crop_mode = self.crop_mode
        self.processor.overwrite = overwrite

        # Connect signals
        self.processor.progress.connect(self.update_progress)
        self.processor.log_message.connect(self.log_message)
        self.processor.processing_file.connect(self.update_current_file)
        self.processor.finished_success.connect(self.processing_finished)
        self.processor.error_occurred.connect(self.processing_error)

        self.processor.start()

    def stop_processing(self):
        if self.processor:
            self.processor.stop()
            self.status_label.setText("Stopping...")
            self.stop_btn.setEnabled(False)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_current_file(self, filename):
        self.current_file_label.setText(f"Processing: {filename}")

    def processing_finished(self, processed, skipped, failed):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.preview_btn.setEnabled(True)
        self.input_edit.setEnabled(True)
        self.output_edit.setEnabled(True)

        self.progress_bar.setValue(100)
        self.current_file_label.clear()
        self.status_label.setText("Finished")

        results = (f"✅ Processed: {processed} | "
                   f"⏭️ Skipped: {skipped} | "
                   f"❌ Failed: {failed}")
        self.results_label.setText(results)

        if processed > 0:
            self.log_message(f"\n🎉 Processing completed successfully!")
            self.log_message(f"Output directory: {self.output_edit.text()}")

            # Ask to open output directory
            reply = QMessageBox.question(self, "Success",
                                         "Processing completed! Open output directory?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                output_dir = self.output_edit.text()
                if sys.platform == "win32":
                    os.startfile(output_dir)
                elif sys.platform == "darwin":
                    os.system(f'open "{output_dir}"')
                else:
                    os.system(f'xdg-open "{output_dir}"')

    def processing_error(self, error_message):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.preview_btn.setEnabled(True)
        self.input_edit.setEnabled(True)
        self.output_edit.setEnabled(True)

        self.status_label.setText("Error occurred")
        self.current_file_label.clear()
        self.log_message(f"❌ ERROR: {error_message}")
        QMessageBox.critical(self, "Processing Error", error_message)


def main():
    # Command line interface (for backward compatibility)
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        # Old CLI mode
        parser = argparse.ArgumentParser(
            description='Image converter to 800×480 JPEG format with BLACK background'
        )
        parser.add_argument('--overwrite', '-o', action='store_true',
                            help='Overwrite existing files')
        parser.add_argument('--crop', '-c', action='store_true',
                            help='Crop mode (default - with BLACK background)')
        parser.add_argument('--settings', '-s', action='store_true',
                            help='Show current settings and exit')

        args = parser.parse_args()

        # Here you could call the old CLI function
        # For now, just show a message
        print("CLI mode is deprecated. Please use the GUI version.")
        return

    # GUI mode
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern style

    # Set application icon if available
    try:
        app_icon = QIcon()
        app_icon.addFile('icon.png')
        app.setWindowIcon(app_icon)
    except:
        pass

    window = ImageConverterUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()