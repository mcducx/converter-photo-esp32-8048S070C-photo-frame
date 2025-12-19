# Image Converter for Digital Photo Farme

A universal image converter for preparing content for 800×480 pixel displays.

## 📋 Description

The script automatically processes photos of various formats and converts them to a unified standard:
- **Size:** 480×800 pixels
- **Format:** RGB JPEG (non-progressive)
- **Background:** Black (for images with different aspect ratios)
- **Support:** All popular formats, including RAW and HEIC

## ✨ Features

- **Automatic processing** of multiple images
- **RAW file support** (CR2, NEF, ARW, etc.)
- **HEIF/HEIC support** (iPhone formats)
- **Two processing modes:** with black background or cropping
- **Intelligent scaling** with aspect ratio preservation
- **Overwrite protection** (optional)
- **Detailed log** of the processing

## 📁 Supported Formats

### Common formats:
- JPEG/JPG, PNG, BMP, TIFF/TIF
- WebP, GIF

### Special formats:
- **HEIF/HEIC** (requires `pillow-heif`)
- **RAW files:**
  - Canon: `.cr2`, `.cr3`
  - Nikon: `.nef`
  - Sony: `.arw`
  - Adobe: `.dng`
  - Fujifilm: `.raf`
  - Olympus: `.orf`
  - Panasonic: `.rw2`

## 🚀 Quick Start

### 1. Install Python
Requires Python 3.7 or higher. Download from [official website](https://python.org).

### 2. Install dependencies:
```bash
pip install Pillow pillow-heif rawpy
```

### 3. Configure paths:
Open `converter.py` and modify the paths at the beginning of the file:

```python
INPUT_DIRECTORY = r"C:\Path\To\Your\Photos"
OUTPUT_DIRECTORY = r"C:\Path\For\Results"
```

### 4. Start conversion:
```bash
python converter.py
```

## ⚙️ Configuration

### Configuration parameters (at the beginning of converter.py):

```python
# Final image size
TARGET_SIZE = (800, 480)

# JPEG quality (1-100)
JPEG_QUALITY = 95

# Background color (RGB)
BACKGROUND_COLOR = (0, 0, 0)  # Black
```

### System dependencies (optional):

**Windows:** Install [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) for RAW support.

**Ubuntu/Debian:**
```bash
sudo apt-get install libheif-dev libraw-dev
```

**macOS:**
```bash
brew install libheif libraw
```

## 🎯 Usage

### Basic commands:

```bash
# Standard processing (skips already processed)
python converter.py

# Overwrite existing files
python converter.py --overwrite

# Crop mode (instead of adding background)
python converter.py --crop

# Combined mode: crop with overwrite
python converter.py --overwrite --crop

# Show current settings
python converter.py --settings
```

### Command line parameters:
| Parameter | Short version | Description |
|----------|----------------|----------|
| `--overwrite` | `-o` | Overwrite existing files |
| `--crop` | `-c` | Crop mode instead of adding background |
| `--settings` | `-s` | Show settings and exit |

## 🔧 How It Works

### Default mode (with black background):
1. Image is opened and converted to RGB
2. Aspect ratio is preserved, image is fitted into 800×480
3. Black background is added around the image
4. Saved as JPEG with 95% quality

### Crop mode (`--crop`):
1. Image is scaled so that one side is at least the target size
2. Central 800×480 part is cropped
3. Saved as JPEG

### RAW file processing:
- Uses AHD demosaicing algorithm
- Applies camera white balance
- Converts to sRGB color space
- 8 bits per channel (JPEG standard)

## 📊 Example Output

```
🖼️  Image Converter v3.0
🎨 Background color: BLACK
📸 Support: CR2, NEF, ARW and other RAW formats
============================================================
✅ Input folder: C:\Photos\Source
✅ Output folder: C:\Photos\Processed

📁 Analyzing folders...
   Supported formats: .jpg, .jpeg, .png, .bmp, .tiff, .tif, .webp, .gif, .heif, .heic, .hif, .cr2, .cr3, .nef, .arw, .dng, .raf, .orf, .rw2
   ✅ HEIF/HEIC: SUPPORTED
   ✅ RAW files (CR2, NEF, etc.): SUPPORTED

📊 Found images: 15
   Target size: 800×480 pixels
   Background color: BLACK (RGB(0, 0, 0))
   Mode: With BLACK background
------------------------------------------------------------
✅ [1/15] Processed: photo1.jpg
✅ [2/15] Processed: image.heic
✅ [3/15] Processed: raw_image.cr2
⏭️  [4/15] Skipped (already exists): photo2.jpg
...
```

## 📁 Project Structure

```
image-converter/
├── converter.py          # Main script
├── README.md            # Documentation
```

## ❓ Frequently Asked Questions

### Q: How to change the background color?
**A:** Change the `BACKGROUND_COLOR` value in the script settings. For example:
- White: `(255, 255, 255)`
- Red: `(255, 0, 0)`
- Blue: `(0, 0, 255)`

### Q: Why aren't RAW files being processed?
**A:** Make sure:
1. All dependencies are installed (`pip install rawpy`)
2. Visual C++ Redistributable is installed on Windows
3. Files are not corrupted

### Q: Are EXIF data preserved?
**A:** No, EXIF data is not preserved to reduce file size and standardize output.

### Q: Can I change the output image size?
**A:** Yes, change the `TARGET_SIZE` value in the script settings.

### Q: How to process subfolders?
**A:** Current version only processes files in the specified folder. For recursive processing, script modification is required.

## 🐛 Debugging

### Installation check:
```bash
python converter.py --settings
```

### Test run:
```bash
# Create a test folder with several images
mkdir test_input
cp some_images.jpg test_input/

# Run conversion
python converter.py
```

## 📞 Support

If you encounter problems:
1. Check if all dependencies are installed
2. Verify folder paths are correct
3. Enable `--settings` mode to check configuration

---

**Version:** 3.0  
**Last update:** 2024  
**Python support:** 3.7+
