import os
import sys
from PIL import Image
import argparse

# =============================================
# PATH SETTINGS (MODIFY HERE FOR YOUR NEEDS)
# =============================================

# Hardcoded paths (change these to your own)
INPUT_DIRECTORY = r"/Users/mcducx/Downloads/input"  # Folder with source images
OUTPUT_DIRECTORY = r"/Users/mcducx/Downloads/output"  # Folder for results

# =============================================
# PROCESSING CONSTANTS (can be modified)
# =============================================
TARGET_SIZE = (480, 800)  # Target size (width, height)
JPEG_QUALITY = 95  # JPEG quality (1-100)
BACKGROUND_COLOR = (0, 0, 0)  # Background color - BLACK (0, 0, 0)

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
    print("ℹ️  Warning: pillow-heif library is not installed. HEIF/HEIC will not be supported.")
    print("   Install: pip install pillow-heif")
except Exception as e:
    HAS_HEIF = False
    print(f"⚠️  Warning: Failed to initialize HEIF support: {e}")

# RAW file support (CR2, NEF, etc.)
try:
    import rawpy

    HAS_RAW = True
except ImportError:
    HAS_RAW = False
    print("ℹ️  Warning: rawpy library is not installed. RAW files (CR2, NEF, etc.) will not be supported.")
    print("   Install: pip install rawpy")
    print("   Additionally on Windows you may need to install Microsoft Visual C++ Redistributable")


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


def process_raw_image(input_path):
    """Processes a RAW file and returns a PIL Image"""
    try:
        # Open RAW file with rawpy
        with rawpy.imread(input_path) as raw:
            # Convert RAW to RGB
            rgb = raw.postprocess(
                use_camera_wb=True,  # Use camera white balance
                half_size=False,  # Full size
                no_auto_bright=False,  # Auto brightness
                output_bps=8,  # 8 bits per channel
                output_color=rawpy.ColorSpace.sRGB,  # sRGB color space
                gamma=(2.222, 4.5),  # Standard gamma
                user_black=None,  # Auto black point
                user_sat=None,  # Auto saturation
                no_auto_scale=False,  # Auto scaling
                demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD  # Demosaicing algorithm
            )

        # Convert numpy array to PIL Image
        img = Image.fromarray(rgb)
        return img

    except Exception as e:
        print(f"❌ Error processing RAW file {os.path.basename(input_path)}: {e}")
        raise


def check_directories():
    """Checks if directories exist and creates them if necessary"""
    if not os.path.exists(INPUT_DIRECTORY):
        print(f"❌ ERROR: Input directory does not exist!")
        print(f"   Path: {INPUT_DIRECTORY}")
        print("\nPossible solutions:")
        print("1. Create the folder at the specified location")
        print("2. Change the path in the script settings (INPUT_DIRECTORY variable)")
        return False

    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)

    print(f"✅ Input directory: {INPUT_DIRECTORY}")
    print(f"✅ Output directory: {OUTPUT_DIRECTORY}")
    return True


def process_image(input_path, output_path, crop_mode=False):
    """Processes a single image"""
    try:
        # Determine file format
        _, ext = os.path.splitext(input_path)
        ext_lower = ext.lower()

        # Process RAW files separately
        if HAS_RAW and ext_lower in ('.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.orf', '.rw2'):
            img = process_raw_image(input_path)
        else:
            # Open regular formats
            img = Image.open(input_path)

        # Convert to RGB (if CMYK, grayscale, etc.)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create BLACK background for transparent images
            rgb_img = Image.new('RGB', img.size, BACKGROUND_COLOR)
            if img.mode == 'P':
                img = img.convert('RGBA')
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        if crop_mode:
            # Crop mode (preserves central part)
            # Resize so that one dimension is at least the target size
            img.thumbnail((TARGET_SIZE[0] * 2, TARGET_SIZE[1] * 2), Image.Resampling.LANCZOS)

            # Crop to center
            left = max(0, (img.width - TARGET_SIZE[0]) // 2)
            top = max(0, (img.height - TARGET_SIZE[1]) // 2)
            right = min(img.width, left + TARGET_SIZE[0])
            bottom = min(img.height, top + TARGET_SIZE[1])

            img = img.crop((left, top, right, bottom))

            # If image is smaller than target size, upscale
            if img.size != TARGET_SIZE:
                img = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)

            new_img = img
        else:
            # Mode with BLACK background addition (preserves proportions)
            img.thumbnail(TARGET_SIZE, Image.Resampling.LANCZOS)

            # Create new image of target size with BLACK background
            new_img = Image.new('RGB', TARGET_SIZE, BACKGROUND_COLOR)

            # Paste image in center
            offset = (
                (TARGET_SIZE[0] - img.size[0]) // 2,
                (TARGET_SIZE[1] - img.size[1]) // 2
            )
            new_img.paste(img, offset)

        # Save as JPEG without progressive
        new_img.save(output_path, 'JPEG', quality=JPEG_QUALITY, optimize=True, progressive=False)

        return True

    except Exception as e:
        print(f"❌ Error processing {os.path.basename(input_path)}: {e}")
        return False


def process_directory(overwrite=False, crop_mode=False):
    """Processes all images in directory"""
    # Check directories
    if not check_directories():
        return

    # Get supported formats
    supported_formats = get_supported_formats()

    print(f"\n📁 Analyzing directories...")
    print(f"   Supported formats: {', '.join(supported_formats)}")

    # Display information about supported formats
    if HAS_HEIF:
        print(f"   ✅ HEIF/HEIC: SUPPORTED")
    else:
        print(f"   ⚠️  HEIF/HEIC: NOT SUPPORTED (install pillow-heif)")

    if HAS_RAW:
        print(f"   ✅ RAW files (CR2, NEF, etc.): SUPPORTED")
    else:
        print(f"   ⚠️  RAW files: NOT SUPPORTED (install rawpy)")

    # Get list of files
    files = os.listdir(INPUT_DIRECTORY)
    image_files = []

    for filename in files:
        _, ext = os.path.splitext(filename)
        if ext.lower() in supported_formats:
            image_files.append(filename)

    if not image_files:
        print(f"\n⚠️  No supported images found in folder {INPUT_DIRECTORY}!")
        return

    print(f"\n📊 Images found: {len(image_files)}")
    print(f"   Target size: {TARGET_SIZE[0]}×{TARGET_SIZE[1]} pixels")
    print(f"   Background color: BLACK (RGB{BACKGROUND_COLOR})")
    print(f"   Mode: {'Crop' if crop_mode else 'With BLACK background'}")
    print("-" * 60)

    # Counters
    processed = 0
    skipped = 0
    failed = 0

    # Process images
    for i, filename in enumerate(image_files, 1):
        input_path = os.path.join(INPUT_DIRECTORY, filename)

        # Create output filename
        name_without_ext = os.path.splitext(filename)[0]
        output_filename = f"{name_without_ext}.jpg"
        output_path = os.path.join(OUTPUT_DIRECTORY, output_filename)

        # Check if file already exists
        if os.path.exists(output_path) and not overwrite:
            print(f"⏭️  [{i}/{len(image_files)}] Skipped (already exists): {filename}")
            skipped += 1
            continue

        # Process image
        if process_image(input_path, output_path, crop_mode):
            processed += 1
            print(f"✅ [{i}/{len(image_files)}] Processed: {filename}")
        else:
            failed += 1
            print(f"❌ [{i}/{len(image_files)}] Error: {filename}")

    # Summary
    print("\n" + "=" * 60)
    print("📊 PROCESSING RESULTS:")
    print("=" * 60)
    print(f"✅ Successfully processed: {processed}")
    print(f"⏭️  Skipped (already exist): {skipped}")
    print(f"❌ Failed to process: {failed}")
    print(f"📂 Output directory: {OUTPUT_DIRECTORY}")

    if processed > 0:
        print("\n🎉 Processing completed successfully!")
        print(f"All images now have BLACK background")
    else:
        print("\nℹ️  Nothing processed. Check path settings.")


def show_settings():
    """Displays current settings"""
    print("\n" + "=" * 60)
    print("⚙️  CURRENT SETTINGS:")
    print("=" * 60)
    print(f"Input directory: {INPUT_DIRECTORY}")
    print(f"Output directory: {OUTPUT_DIRECTORY}")
    print(f"Target size: {TARGET_SIZE[0]}×{TARGET_SIZE[1]}")
    print(f"JPEG quality: {JPEG_QUALITY}%")
    print(f"Background color: BLACK (RGB{BACKGROUND_COLOR})")
    print(f"HEIF support: {'✅' if HAS_HEIF else '❌ (install pillow-heif)'}")
    print(f"RAW support: {'✅' if HAS_RAW else '❌ (install rawpy)'}")
    print("=" * 60)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Image converter to 800×480 JPEG format with BLACK background',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f'''
Usage examples:
  %(prog)s                    # Normal processing with BLACK background
  %(prog)s --overwrite        # Overwrite existing files
  %(prog)s --crop             # Crop mode (without adding background)
  %(prog)s --settings         # Show settings and exit
  %(prog)s --overwrite --crop # Overwrite in crop mode

Supported RAW formats:
  CR2, CR3 (Canon), NEF (Nikon), ARW (Sony), DNG (Adobe), 
  RAF (Fujifilm), ORF (Olympus), RW2 (Panasonic)

Required libraries:
  • pillow-heif for HEIF/HEIC
  • rawpy for RAW files

Note: BLACK background (0, 0, 0) is used by default
        '''
    )

    parser.add_argument('--overwrite', '-o', action='store_true',
                        help='Overwrite existing files')
    parser.add_argument('--crop', '-c', action='store_true',
                        help='Crop mode (default - with BLACK background)')
    parser.add_argument('--settings', '-s', action='store_true',
                        help='Show current settings and exit')

    args = parser.parse_args()

    print("🖼️  Image Converter v3.0")
    print("🎨 Background color: BLACK")
    print("📸 Support: CR2, NEF, ARW and other RAW formats")
    print("=" * 60)

    if args.settings:
        show_settings()
        return

    print("Before starting, check path settings in the script:")
    print(f"  Input directory: {INPUT_DIRECTORY}")
    print(f"  Output directory: {OUTPUT_DIRECTORY}")

    # Check if input directory exists
    if not os.path.exists(INPUT_DIRECTORY):
        print(f"\n❌ ERROR: Input directory does not exist!")
        print(f"   Path: {INPUT_DIRECTORY}")
        print("\nChange the path in script settings:")
        print("1. Open the script file in a text editor")
        print("2. Find lines with INPUT_DIRECTORY and OUTPUT_DIRECTORY")
        print("3. Specify correct paths to your folders")
        input("\nPress Enter to exit...")
        return

    # Overwrite warning
    if args.overwrite:
        print("\n⚠️  OVERWRITE MODE ENABLED! Existing files will be overwritten.")

    if args.crop:
        print("\nℹ️  Mode: CROP (images will be cropped to 800×480)")
    else:
        print(f"\nℹ️  Mode: WITH BLACK BACKGROUND (images will preserve proportions on black background)")

    # Start processing
    process_directory(args.overwrite, args.crop)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        print("Check settings and try again.")

    input("\nPress Enter to exit...")
