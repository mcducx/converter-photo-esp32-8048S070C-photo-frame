# ImageFlow

## 🖼️ Batch Image Converter with Intelligent Processing

Image Converter is a powerful, user-friendly desktop application for batch image conversion and resizing. It supports a wide range of image formats including RAW camera files and iPhone HEIC/HEIF formats, with intelligent automatic processing mode selection.

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

### 🎨 Modern User Interface
- **Dark Theme**: Clean, professional dark interface
- **Real-time Progress**: Live progress bar and file-by-file logging
- **Detailed Statistics**: Complete processing reports
- **Intuitive Controls**: Easy-to-use directory selection and settings

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
*Executable files for macOS and Linux for easy installation are available in the releases(https://github.com/mcducx/converter-photo-esp32-8048S070C-photo-frame/releases/tag/1.0).*

## 🚀 Usage

### Basic Workflow
1. **Select Input Directory**: Choose folder containing images to convert
2. **Select Output Directory**: Choose where to save converted images
3. **Configure Settings**: Set resolution, quality, and processing mode
4. **Start Processing**: Click "Start Processing" to begin batch conversion

### Settings Guide

#### Resolution Settings
- **Width & Height**: Set target dimensions in pixels (default: 480×800)
- **Aspect Ratio Display**: Shows current aspect ratio with common ratio equivalents

#### Quality Settings
- **JPEG Quality**: 95% recommended for optimal balance of quality and file size
- **Quality Slider**: Easy adjustment from 50% (smaller files) to 100% (best quality)

#### Processing Mode
- **🤖 Auto**: Smart mode that analyzes each image's aspect ratio and chooses the best method
- **🖼 Fit**: Preserves entire image, adds background if needed
- **✂️ Crop**: Centers and crops to exact target dimensions

#### Background Color (Fit/Auto modes only)
- **Preset Colors**: Black, white, or gray
- **Custom Color**: Choose any color using color picker

#### File Handling
- **Overwrite Existing**: Toggle to overwrite files in output directory
- **Add Suffix**: Append "_converted" to output filenames

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

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

### Third-Party Licenses
- **PyQt5**: GPL v3 or commercial
- **Pillow**: Historical PIL License (MIT-like)
- **rawpy**: MIT License
- **pillow_heif**: MIT License

## 🔄 Changelog

### Version 3.0
- Added intelligent Auto mode
- Support for RAW camera formats
- HEIF/HEIC (iPhone) format support
- Modern dark theme interface
- Enhanced error handling and logging

### Version 2.0
- Multi-threaded background processing
- Custom resolution settings
- Quality control slider
- Background color options

### Version 1.0
- Basic batch conversion
- Support for common formats
- Simple GUI interface

---

**Image Converter** - batch image processing made simple. Convert, resize, and optimize your images with intelligent automation and extensive format support.
