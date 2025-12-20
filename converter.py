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
        self.background_color = (0, 0, 0)
        self.crop_mode = "fit"  # "fit", "crop", or "auto"
        self.overwrite = False
        self.running = True
        self.processed_files = []
        self.failed_files = []

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

            # Определяем режим обработки
            actual_crop_mode = self.crop_mode
            if actual_crop_mode == "auto":
                # Автоматический выбор: если изображение близко к целевому соотношению сторон - кроп, иначе - фит с полями
                target_ratio = self.target_size[0] / self.target_size[1]
                image_ratio = img.width / img.height

                # Если разница в соотношениях сторон менее 20%, используем кроп
                if abs(image_ratio - target_ratio) / target_ratio < 0.2:
                    actual_crop_mode = "crop"
                else:
                    actual_crop_mode = "fit"

            if actual_crop_mode == "crop":
                img.thumbnail((self.target_size[0] * 2, self.target_size[1] * 2), Image.Resampling.LANCZOS)
                left = max(0, (img.width - self.target_size[0]) // 2)
                top = max(0, (img.height - self.target_size[1]) // 2)
                right = min(img.width, left + self.target_size[0])
                bottom = min(img.height, top + self.target_size[1])
                img = img.crop((left, top, right, bottom))

                if img.size != self.target_size:
                    img = img.resize(self.target_size, Image.Resampling.LANCZOS)
                new_img = img
            else:  # "fit" mode
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
                            self.processed_files.append(filename)
                            self.log_message.emit(f"Processed: {filename}")
                        else:
                            failed += 1
                            self.failed_files.append(filename)
                            self.log_message.emit(f"Failed: {filename}")
                    except Exception as e:
                        failed += 1
                        self.failed_files.append(filename)
                        self.log_message.emit(f"Error: {filename} - {str(e)}")

                progress = int((i + 1) / total * 100)
                self.progress.emit(progress)

            if self.running:
                self.finished_success.emit(processed, skipped, failed)

        except Exception as e:
            self.error_occurred.emit(f"Processing error: {str(e)}")


class ProcessingOptionsWidget(QWidget):
    """Widget for processing options with compact layout"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # File handling options
        file_group = QGroupBox("File Handling")
        file_group.setStyleSheet("""
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

        file_layout = QVBoxLayout()
        file_layout.setContentsMargins(10, 15, 10, 15)
        file_layout.setSpacing(10)

        # Overwrite checkbox
        self.overwrite_check = QCheckBox(" Overwrite existing files")
        self.overwrite_check.setToolTip("Overwrite existing files in output directory")

        # Add suffix checkbox
        self.suffix_check = QCheckBox(" Add '_converted' suffix")
        self.suffix_check.setToolTip("Add suffix to output filenames")

        file_layout.addWidget(self.overwrite_check)
        file_layout.addWidget(self.suffix_check)

        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)

    def get_options(self):
        """Return all options as dict"""
        return {
            'overwrite': self.overwrite_check.isChecked(),
            'add_suffix': self.suffix_check.isChecked()
        }


class SettingsDialog(QDialog):
    """Settings dialog window with all processing options"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Settings")
        self.setFixedSize(450, 550)
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
            QSlider::groove:horizontal {
                height: 6px;
                background: #3c3c3c;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #0066cc;
                width: 18px;
                height: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #0077dd;
            }
        """)

        layout = QVBoxLayout()

        # Resolution Settings
        res_group = QGroupBox("Resolution Settings")
        res_layout = QVBoxLayout()
        res_layout.setSpacing(15)

        # Width and Height
        size_layout = QHBoxLayout()

        # Width
        width_layout = QVBoxLayout()
        width_layout.setSpacing(5)
        width_layout.addWidget(QLabel("Width:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 4000)
        self.width_spin.setValue(self.parent.target_width)
        self.width_spin.setSuffix(" px")
        self.width_spin.valueChanged.connect(self.update_resolution)
        width_layout.addWidget(self.width_spin)
        size_layout.addLayout(width_layout)

        size_layout.addSpacing(20)

        # Height
        height_layout = QVBoxLayout()
        height_layout.setSpacing(5)
        height_layout.addWidget(QLabel("Height:"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 4000)
        self.height_spin.setValue(self.parent.target_height)
        self.height_spin.setSuffix(" px")
        self.height_spin.valueChanged.connect(self.update_resolution)
        height_layout.addWidget(self.height_spin)
        size_layout.addLayout(height_layout)

        size_layout.addStretch()
        res_layout.addLayout(size_layout)

        # Aspect ratio info
        self.aspect_ratio_label = QLabel("Aspect ratio: 0.60 (3:5)")
        self.aspect_ratio_label.setStyleSheet("color: #888888; font-size: 11px; font-style: italic;")
        res_layout.addWidget(self.aspect_ratio_label)

        # Update aspect ratio when values change
        self.width_spin.valueChanged.connect(self.update_aspect_ratio)
        self.height_spin.valueChanged.connect(self.update_aspect_ratio)
        self.update_aspect_ratio()

        res_group.setLayout(res_layout)
        layout.addWidget(res_group)

        # Quality Settings
        quality_group = QGroupBox("Quality Settings")
        quality_layout = QVBoxLayout()
        quality_layout.setSpacing(10)

        # Quality slider
        quality_slider_layout = QHBoxLayout()
        quality_slider_layout.addWidget(QLabel("JPEG Quality:"))

        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(50, 100)
        self.quality_slider.setValue(self.parent.jpeg_quality)
        self.quality_slider.setTickPosition(QSlider.TicksBelow)
        self.quality_slider.setTickInterval(10)

        self.quality_label = QLabel(f"{self.parent.jpeg_quality}%")
        self.quality_label.setFixedWidth(40)
        self.quality_label.setAlignment(Qt.AlignCenter)

        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_label.setText(f"{v}%")
        )

        quality_slider_layout.addWidget(self.quality_slider)
        quality_slider_layout.addWidget(self.quality_label)
        quality_layout.addLayout(quality_slider_layout)

        # Quality info
        quality_info = QLabel("Higher quality = larger file size (95% recommended)")
        quality_info.setStyleSheet("color: #888888; font-size: 11px; font-style: italic;")
        quality_layout.addWidget(quality_info)

        quality_group.setLayout(quality_layout)
        layout.addWidget(quality_group)

        # Processing Mode & Background
        mode_bg_group = QGroupBox("Processing Mode & Background")
        mode_bg_layout = QVBoxLayout()
        mode_bg_layout.setSpacing(15)

        # Mode selection - теперь 3 кнопки
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Processing Mode:"))

        # Mode toggle widget
        mode_toggle_layout = QHBoxLayout()
        mode_toggle_layout.setSpacing(5)

        # Auto mode button
        self.auto_btn = QPushButton("🤖 Auto")
        self.auto_btn.setCheckable(True)
        self.auto_btn.setChecked(self.parent.crop_mode == "auto")
        self.auto_btn.setToolTip("Automatically choose between crop and fit based on image aspect ratio")
        self.auto_btn.clicked.connect(lambda: self.set_mode("auto"))
        self.auto_btn.setFixedWidth(100)

        # Fit mode button
        self.fit_btn = QPushButton("🖼 Fit")
        self.fit_btn.setCheckable(True)
        self.fit_btn.setChecked(self.parent.crop_mode == "fit")
        self.fit_btn.setToolTip("Fit image within target size with background")
        self.fit_btn.clicked.connect(lambda: self.set_mode("fit"))
        self.fit_btn.setFixedWidth(100)

        # Crop mode button
        self.crop_btn = QPushButton("✂️ Crop")
        self.crop_btn.setCheckable(True)
        self.crop_btn.setChecked(self.parent.crop_mode == "crop")
        self.crop_btn.setToolTip("Crop image to exact target size")
        self.crop_btn.clicked.connect(lambda: self.set_mode("crop"))
        self.crop_btn.setFixedWidth(100)

        # Group for mode buttons
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.auto_btn)
        self.mode_group.addButton(self.fit_btn)
        self.mode_group.addButton(self.crop_btn)

        mode_toggle_layout.addWidget(self.auto_btn)
        mode_toggle_layout.addWidget(self.fit_btn)
        mode_toggle_layout.addWidget(self.crop_btn)

        mode_layout.addLayout(mode_toggle_layout)
        mode_layout.addStretch()
        mode_bg_layout.addLayout(mode_layout)


        # Background color selection (visible only in Fit and Auto modes)
        self.bg_color_widget = QWidget()
        bg_color_layout = QVBoxLayout(self.bg_color_widget)
        bg_color_layout.setContentsMargins(0, 0, 0, 0)
        bg_color_layout.setSpacing(5)

        bg_label_layout = QHBoxLayout()
        bg_label_layout.addWidget(QLabel("Background Color:"))
        bg_label_layout.addStretch()
        bg_color_layout.addLayout(bg_label_layout)

        # Background color buttons
        bg_buttons_layout = QHBoxLayout()

        # Black button with white text
        self.bg_black = QPushButton("⬛ Black")
        self.bg_black.setCheckable(True)
        self.bg_black.setChecked(self.parent.background_color == (0, 0, 0))
        self.bg_black.setToolTip("Black background")
        self.bg_black.clicked.connect(lambda: self.set_background('black'))

        # White button with black text
        self.bg_white = QPushButton("⬜ White")
        self.bg_white.setCheckable(True)
        self.bg_white.setChecked(self.parent.background_color == (255, 255, 255))
        self.bg_white.setToolTip("White background")
        self.bg_white.clicked.connect(lambda: self.set_background('white'))

        # Gray button with white text
        self.bg_gray = QPushButton("◼ Gray")
        self.bg_gray.setCheckable(True)
        self.bg_gray.setChecked(self.parent.background_color == (128, 128, 128))
        self.bg_gray.setToolTip("Gray background")
        self.bg_gray.clicked.connect(lambda: self.set_background('gray'))

        # Custom color button
        self.bg_custom = QPushButton("🎨 Custom")
        self.bg_custom.setCheckable(True)
        self.bg_custom.setToolTip("Choose custom color")
        self.bg_custom.clicked.connect(lambda: self.set_background('custom'))

        # Check if current color is not black, white, or gray
        if (self.parent.background_color != (0, 0, 0) and
                self.parent.background_color != (255, 255, 255) and
                self.parent.background_color != (128, 128, 128)):
            self.bg_custom.setChecked(True)

        # Group for background buttons
        bg_group_buttons = QButtonGroup(self)
        bg_group_buttons.addButton(self.bg_black)
        bg_group_buttons.addButton(self.bg_white)
        bg_group_buttons.addButton(self.bg_gray)
        bg_group_buttons.addButton(self.bg_custom)

        bg_buttons_layout.addWidget(self.bg_black)
        bg_buttons_layout.addWidget(self.bg_white)
        bg_buttons_layout.addWidget(self.bg_gray)
        bg_buttons_layout.addWidget(self.bg_custom)
        bg_buttons_layout.addStretch()

        bg_color_layout.addLayout(bg_buttons_layout)
        mode_bg_layout.addWidget(self.bg_color_widget)

        mode_bg_group.setLayout(mode_bg_layout)
        layout.addWidget(mode_bg_group)

        # Format support info
        info_label = QLabel(f"HEIF support: {'Yes' if HAS_HEIF else 'No'}\n"
                            f"RAW support: {'Yes' if HAS_RAW else 'No'}\n"
                            f"Supported formats: {', '.join([f[1:] for f in get_supported_formats()])}")
        info_label.setStyleSheet(
            "color: #888888; font-size: 11px; padding: 10px; background-color: #3c3c3c; border-radius: 4px;")
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

        # Initialize styles and visibility
        self.style_buttons()
        self.update_mode_visibility()

    def update_resolution(self):
        """Update resolution display"""
        pass  # Just updates the display, actual saving happens in save_settings

    def update_aspect_ratio(self):
        """Update aspect ratio label"""
        width = self.width_spin.value()
        height = self.height_spin.value()

        if height > 0:
            ratio = width / height
            # Find common aspect ratio
            common_ratios = [
                (1.0, "1:1"),
                (1.33, "4:3"),
                (1.5, "3:2"),
                (1.67, "5:3"),
                (1.78, "16:9"),
                (0.75, "3:4"),
                (0.67, "2:3"),
                (0.56, "9:16"),
                (0.6, "3:5"),
                (0.8, "4:5"),
            ]

            closest_ratio = None
            min_diff = float('inf')

            for common_ratio, ratio_str in common_ratios:
                diff = abs(ratio - common_ratio)
                if diff < min_diff:
                    min_diff = diff
                    closest_ratio = ratio_str

            if min_diff < 0.05:  # If close to a common ratio
                ratio_text = f"{ratio:.2f} ({closest_ratio})"
            else:
                ratio_text = f"{ratio:.2f}"

            self.aspect_ratio_label.setText(f"Aspect ratio: {ratio_text}")
        else:
            self.aspect_ratio_label.setText("Aspect ratio: N/A")

    def set_mode(self, mode):
        """Set processing mode"""
        self.parent.crop_mode = mode
        self.auto_btn.setChecked(mode == "auto")
        self.fit_btn.setChecked(mode == "fit")
        self.crop_btn.setChecked(mode == "crop")
        self.update_mode_visibility()
        self.style_buttons()

    def update_mode_visibility(self):
        """Update visibility based on mode"""
        is_crop_mode = self.crop_btn.isChecked()
        self.bg_color_widget.setVisible(not is_crop_mode)

    def set_background(self, color):
        """Set background color"""
        if color == 'black':
            self.parent.background_color = (0, 0, 0)
            self.bg_black.setChecked(True)
        elif color == 'white':
            self.parent.background_color = (255, 255, 255)
            self.bg_white.setChecked(True)
        elif color == 'gray':
            self.parent.background_color = (128, 128, 128)
            self.bg_gray.setChecked(True)
        elif color == 'custom':
            self.choose_custom_color()

        self.style_buttons()

    def choose_custom_color(self):
        """Open color picker for custom background"""
        color = QColorDialog.getColor(QColor(*self.parent.background_color), self, "Choose Background Color")
        if color.isValid():
            self.parent.background_color = (color.red(), color.green(), color.blue())
            self.bg_custom.setChecked(True)
            self.style_buttons()

    def style_buttons(self):
        """Apply styling to all buttons"""
        # Mode buttons styling
        mode_checked_style = """
            QPushButton {
                background-color: #0066cc;
                color: white;
                border: 2px solid #0055aa;
                border-radius: 4px;
                padding: 8px 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0077dd;
            }
        """

        mode_unchecked_style = """
            QPushButton {
                background-color: #404040;
                color: white;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """

        self.auto_btn.setStyleSheet(mode_checked_style if self.auto_btn.isChecked() else mode_unchecked_style)
        self.fit_btn.setStyleSheet(mode_checked_style if self.fit_btn.isChecked() else mode_unchecked_style)
        self.crop_btn.setStyleSheet(mode_checked_style if self.crop_btn.isChecked() else mode_unchecked_style)

        # Background buttons styling with proper contrast
        if self.bg_black.isChecked():
            self.bg_black.setStyleSheet("""
                QPushButton {
                    background-color: black;
                    color: white;
                    border: 2px solid #0066cc;
                    border-radius: 4px;
                    padding: 6px 10px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #333333;
                }
            """)
        else:
            self.bg_black.setStyleSheet("""
                QPushButton {
                    background-color: black;
                    color: white;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 6px 10px;
                }
                QPushButton:hover {
                    background-color: #333333;
                    border: 1px solid #666666;
                }
            """)

        if self.bg_white.isChecked():
            self.bg_white.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    color: black;
                    border: 2px solid #0066cc;
                    border-radius: 4px;
                    padding: 6px 10px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                }
            """)
        else:
            self.bg_white.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    color: black;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 6px 10px;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                    border: 1px solid #666666;
                }
            """)

        if self.bg_gray.isChecked():
            self.bg_gray.setStyleSheet("""
                QPushButton {
                    background-color: #808080;
                    color: white;
                    border: 2px solid #0066cc;
                    border-radius: 4px;
                    padding: 6px 10px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #999999;
                }
            """)
        else:
            self.bg_gray.setStyleSheet("""
                QPushButton {
                    background-color: #808080;
                    color: white;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 6px 10px;
                }
                QPushButton:hover {
                    background-color: #999999;
                    border: 1px solid #666666;
                }
            """)

        # Custom button styling
        custom_bg_color = QColor(*self.parent.background_color)
        text_color = "white" if custom_bg_color.lightness() < 128 else "black"

        if self.bg_custom.isChecked():
            self.bg_custom.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgb({custom_bg_color.red()}, {custom_bg_color.green()}, {custom_bg_color.blue()});
                    color: {text_color};
                    border: 2px solid #0066cc;
                    border-radius: 4px;
                    padding: 6px 10px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: rgb({min(255, custom_bg_color.red() + 20)}, 
                                         {min(255, custom_bg_color.green() + 20)}, 
                                         {min(255, custom_bg_color.blue() + 20)});
                }}
            """)
        else:
            self.bg_custom.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgb({custom_bg_color.red()}, {custom_bg_color.green()}, {custom_bg_color.blue()});
                    color: {text_color};
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 6px 10px;
                }}
                QPushButton:hover {{
                    background-color: rgb({min(255, custom_bg_color.red() + 20)}, 
                                         {min(255, custom_bg_color.green() + 20)}, 
                                         {min(255, custom_bg_color.blue() + 20)});
                    border: 1px solid #666666;
                }}
            """)

    def save_settings(self):
        """Save all settings"""
        self.parent.target_width = self.width_spin.value()
        self.parent.target_height = self.height_spin.value()
        self.parent.target_size = (self.parent.target_width, self.parent.target_height)
        self.parent.jpeg_quality = self.quality_slider.value()

        # Определяем режим
        if self.auto_btn.isChecked():
            self.parent.crop_mode = "auto"
        elif self.fit_btn.isChecked():
            self.parent.crop_mode = "fit"
        else:
            self.parent.crop_mode = "crop"

        # Background color is already set in parent via set_background method
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
        self.crop_mode = "fit"  # По умолчанию auto
        self.processor = None
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Image Converter")
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
        header_label = QLabel("🖼️ Image Converter")
        header_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        header_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header_label)

        sub_label = QLabel("Convert and resize images")
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

        input_btn = QPushButton("📁 Browse...")
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

        output_btn = QPushButton("📁 Browse...")
        output_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(output_btn)
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)

        # Processing Options Widget (only File Handling now)
        self.processing_options = ProcessingOptionsWidget(self)
        main_layout.addWidget(self.processing_options)

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

        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        self.settings_btn.setMinimumHeight(40)

        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.settings_btn)
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

        # Set default paths
        home_dir = os.path.expanduser("~")

        # Пытаемся найти подходящую директорию для ввода
        possible_input_dirs = [
            os.path.join(home_dir, "Downloads", "input")
        ]

        for dir_path in possible_input_dirs:
            if os.path.exists(dir_path):
                self.input_edit.setText(dir_path)
                break

        # Для вывода создаем директорию на рабочем столе
        output_dir = os.path.join(home_dir, "Downloads",  "output")
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except:
                output_dir = home_dir
        self.output_edit.setText(output_dir)

    def browse_input(self):
        # Начинаем с домашней директории
        home_dir = os.path.expanduser("~")
        directory = QFileDialog.getExistingDirectory(self, "Select Input Directory", home_dir)
        if directory:
            self.input_edit.setText(directory)

    def browse_output(self):
        # Начинаем с рабочего стола
        desktop_dir = os.path.join(os.path.expanduser("~"))
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory", desktop_dir)
        if directory:
            self.output_edit.setText(directory)

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec_():
            mode_text = {
                "auto": "Auto (smart selection)",
                "fit": "Fit with background",
                "crop": "Crop to exact size"
            }.get(self.crop_mode, self.crop_mode)

            self.log_message(
                f"Settings updated: {self.target_width}×{self.target_height}, Quality: {self.jpeg_quality}%, Mode: {mode_text}")

    def log_message(self, message):
        timestamp = QTime.currentTime().toString("HH:mm:ss")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def start_processing(self):
        input_dir = self.input_edit.text()
        output_dir = self.output_edit.text()

        if not input_dir or not os.path.exists(input_dir):
            QMessageBox.critical(self, "Error", "Please select a valid input directory!")
            return

        if not output_dir:
            QMessageBox.critical(self, "Error", "Please select an output directory!")
            return

        # Get options from processing options widget
        file_options = self.processing_options.get_options()
        overwrite = file_options['overwrite']
        add_suffix = file_options['add_suffix']

        # Disable controls during processing
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.settings_btn.setEnabled(False)

        # Clear previous results
        self.log_text.clear()
        self.results_label.clear()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Processing...")

        # Log current settings
        mode_text = {
            "auto": "Auto (smart selection)",
            "fit": "Fit with background",
            "crop": "Crop to exact size"
        }.get(self.crop_mode, self.crop_mode)

        self.log_message(f"Starting processing with settings:")
        self.log_message(f"  Resolution: {self.target_width}×{self.target_height}")
        self.log_message(f"  Quality: {self.jpeg_quality}%")
        self.log_message(f"  Mode: {mode_text}")
        if self.crop_mode != "crop":
            self.log_message(f"  Background: RGB{self.background_color}")
        self.log_message(f"  Overwrite: {'Yes' if overwrite else 'No'}")
        self.log_message(f"  Add suffix: {'Yes' if add_suffix else 'No'}")

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
        self.settings_btn.setEnabled(True)

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
        self.settings_btn.setEnabled(True)

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