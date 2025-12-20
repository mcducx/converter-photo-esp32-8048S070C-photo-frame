# ImageFlow

## 🖼️ Batch Image Converter with Intelligent Processing

ImageFlow is a powerful, user-friendly desktop application for batch image conversion and resizing. It supports a wide range of image formats including RAW camera files and iPhone HEIC/HEIF formats, with intelligent automatic processing mode selection.

## ✨ Features

### 🚀 Smart Processing Modes
- **🤖 Auto Mode**: Intelligently chooses between crop and fit based on image aspect ratio
- **🖼 Fit Mode**: Resizes images to fit within target dimensions with background padding
- **✂️ Crop Mode**: Crops images to exact target dimensions (centered)

### 📁 Extensive Format Support
- **Standard formats**: JPG, PNG, BMP, TIFF, WebP, GIF
- **iPhone formats**: HEIF, HEIC (requires pillow_heif)
- **RAW camera formats**: CR2, CR3, NEF, ARW, DNG, RAF, ORF, RW2 (requires rawpy)
- **All images are converted to high-quality JPEG output**

### ⚙️ Advanced Processing Options
- **Custom Resolution**: Set any target dimensions (100-4000px)
- **Quality Control**: Adjustable JPEG quality (50-100%)
- **Background Colors**: Black, white, gray, or custom color
- **File Management**: Overwrite protection and optional filename suffixes
- **Batch Processing**: Process entire folders with one click

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Install from Source

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/image-converter-pro](https://github.com/mcducx/imageflow.git
cd imageflow
```

2. **Install required packages:**
```bash
pip install PyQt5 Pillow
```

3. **Optional: Install format support packages:**
```bash
# For HEIF/HEIC (iPhone) support:
pip install pillow_heif

# For RAW camera file support:
pip install rawpy
```

4. **Run the application:**
```bash
python converter.py
```

### Pre-built Executables
*Coming soon: Windows
*Executable files for macOS and Linux for easy installation are available in the releases(https://github.com/mcducx/imageflow/releases/tag/1.0).*

## 🔧 Supported Formats

### Input Formats
| Format | Extension | Requirement |
|--------|-----------|-------------|
| JPEG | .jpg, .jpeg | Built-in |
| PNG | .png | Built-in |
| BMP | .bmp | Built-in |
| TIFF | .tiff, .tif | Built-in |
| WebP | .webp | Built-in |
| GIF | .gif | Built-in |
| HEIF/HEIC | .heif, .heic, .hif | pillow_heif |
| RAW (Canon) | .cr2, .cr3 | rawpy |
| RAW (Nikon) | .nef | rawpy |
| RAW (Sony) | .arw | rawpy |
| RAW (Adobe) | .dng | rawpy |
| RAW (Fuji) | .raf | rawpy |
| RAW (Olympus) | .orf | rawpy |
| RAW (Panasonic) | .rw2 | rawpy |

### Output Format
- **JPEG (.jpg)**: All images are converted to high-quality JPEG format

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Report Bugs**: Use the issue tracker to report bugs
2. **Feature Requests**: Suggest new features or improvements
3. **Code Contributions**: Submit pull requests
4. **Documentation**: Help improve documentation

### Third-Party Licenses
- **PyQt5**: GPL v3 or commercial
- **Pillow**: Historical PIL License (MIT-like)
- **rawpy**: MIT License
- **pillow_heif**: MIT License

---

**ImageFlow** - batch image processing made simple. Convert, resize, and optimize your images with intelligent automation and extensive format support.
