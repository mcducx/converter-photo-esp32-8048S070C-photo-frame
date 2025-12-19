# Image Converter Pro

A powerful Python-based image conversion tool with a modern GUI interface, designed to convert various image formats to standardized JPEG images with customizable backgrounds or cropping options.

## 🌟 Features

- **Multiple Format Support**: Convert JPG, PNG, BMP, TIFF, WEBP, GIF, HEIF/HEIC (iPhone), and RAW formats (CR2, NEF, ARW, DNG, etc.)
- **Flexible Processing Modes**:
  - Fit with background (adds black/white/custom color padding)
  - Crop to fit (intelligently crops to target dimensions)
- **Customizable Settings**:
  - Adjustable target resolution (default: 800×480)
  - Configurable JPEG quality (1-100%)
  - Custom background colors
  - Overwrite existing files option
- **Modern GUI Interface**: Dark theme with real-time progress tracking
- **Batch Processing**: Convert entire folders of images at once
- **Threaded Processing**: Non-blocking UI during conversion
- **Preview Function**: Check image details before processing
- **Comprehensive Logging**: Detailed processing log with timestamps

## 📋 Prerequisites

### Required Dependencies
- Python 3.7+
- Pillow (PIL Fork)
- PyQt5

### Optional Dependencies for Extended Format Support
- `pillow_heif` - for HEIF/HEIC (iPhone) support
- `rawpy` - for RAW camera format support (CR2, NEF, ARW, etc.)

## 🔧 Installation

1. **Clone or download the repository**
```bash
git clone <repository-url>
cd image-converter-pro
```

2. **Install required packages**
```bash
pip install PyQt5 Pillow
```

3. **Install optional packages for extended format support**
```bash
# For HEIF/HEIC (iPhone) support
pip install pillow-heif

# For RAW camera format support
pip install rawpy
```

## 🚀 Usage

### GUI Mode (Recommended)
1. Run the application:
```bash
python image_converter.py
```

2. **Configure your conversion:**
   - Select input directory containing source images
   - Select output directory for converted JPEGs
   - Choose processing mode:
     - **Fit with background**: Resizes image to fit within target dimensions while maintaining aspect ratio, adding background color
     - **Crop to fit**: Crops image to exactly match target dimensions
   - Adjust settings via "Settings ⚙️" button if needed
   - Click "▶ Start Processing"

### CLI Mode (Deprecated)
```bash
# Basic usage (opens GUI)
python image_converter.py

# Legacy CLI options (deprecated)
python image_converter.py --overwrite
python image_converter.py --crop
```

## 📁 Supported Formats

### Base Formats (always supported)
- `.jpg`, `.jpeg`
- `.png`
- `.bmp`
- `.tiff`, `.tif`
- `.webp`
- `.gif`

### With Optional Dependencies

**HEIF/HEIC Support** (requires `pillow_heif`):
- `.heif`, `.heic`, `.hif`

**RAW Camera Format Support** (requires `rawpy`):
- `.cr2`, `.cr3` (Canon)
- `.nef` (Nikon)
- `.arw` (Sony)
- `.dng` (Adobe Digital Negative)
- `.raf` (Fujifilm)
- `.orf` (Olympus)
- `.rw2` (Panasonic)

## ⚙️ Configuration

Access settings via the "Settings ⚙️" button:

1. **Target Size**: Set output image dimensions (default: 800×480)
2. **JPEG Quality**: Adjust compression quality (1-100%, default: 95%)
3. **Background Color**: Choose from Black, White, Gray, or Custom color
4. **Default Mode**: Set preferred processing mode
5. **Format Support Status**: Shows which optional formats are available

## 📊 Output

All images are converted to JPEG format with the following characteristics:
- Standardized dimensions (configurable, default 800×480)
- RGB color space
- Configurable JPEG quality
- Progressive encoding disabled for compatibility
- Optimized for size/quality balance

## 🖥️ Preview

The application includes a preview function that shows:
- Original image dimensions
- File format
- Color mode
- Target conversion size

## 🔄 Processing Details

### Fit with Background Mode
1. Image is resized (maintaining aspect ratio) to fit within target dimensions
2. Padding is added to reach exact target size
3. Padding color is configurable (default: black)

### Crop to Fit Mode
1. Image is resized (maintaining aspect ratio) to cover target dimensions
2. Center portion is cropped to exact target size
3. Uses LANCZOS resampling for high-quality results

## 🐛 Troubleshooting

### Common Issues

1. **"No supported images found"**
   - Check that input directory contains supported formats
   - Install optional dependencies for HEIF/RAW support if needed

2. **RAW files not processing**
   - Install `rawpy`: `pip install rawpy`
   - Some RAW formats may require additional system libraries

3. **HEIF/HEIC files not processing**
   - Install `pillow_heif`: `pip install pillow-heif`

4. **Memory errors with large images**
   - Reduce JPEG quality setting
   - Process fewer images at once

5. **Application freezes during processing**
   - Processing is done in background thread; UI should remain responsive
   - Check system resources

## 📝 Development

### Project Structure
```
image-converter-pro/
├── image_converter.py    # Main application file
├── README.md            # This documentation
└── requirements.txt     # Python dependencies
```

### Key Components
- `ImageConverterUI`: Main GUI window class
- `ImageProcessor`: Background processing thread
- `SettingsDialog`: Configuration dialog
- `get_supported_formats()`: Dynamic format detection

### Extending Support
To add support for additional formats:
1. Add format extension to `get_supported_formats()` function
2. Implement processing logic in `process_image()` or add specialized handler
3. Update documentation

## 📄 License

This project is provided as-is. Users are free to modify and distribute according to their needs.

## 👥 Author

Created for efficient batch image processing with a focus on format compatibility and ease of use.

## 🔗 Dependencies

- **PyQt5**: GUI framework
- **Pillow**: Image processing
- **pillow_heif** (optional): HEIF/HEIC support
- **rawpy** (optional): RAW format support

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📞 Support

For issues or questions:
1. Check the Troubleshooting section above
2. Ensure all dependencies are properly installed
3. Verify input images are in supported formats
4. Check application logs for detailed error messages

---

**Note**: The CLI interface is deprecated in favor of the more user-friendly GUI interface. Future development will focus on the GUI features.
