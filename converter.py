import os
import sys
from PIL import Image
import argparse

# =============================================
# НАСТРОЙКИ ПУТЕЙ (ИЗМЕНИТЕ ЗДЕСЬ ПОД СВОИ НУЖДЫ)
# =============================================

# Жёстко заданные пути (измените их на свои)
INPUT_DIRECTORY = r"/Users/mcducx/Downloads/input"  # Папка с исходными изображениями
OUTPUT_DIRECTORY = r"/Users/mcducx/Downloads/output"  # Папка для результатов

# =============================================
# КОНСТАНТЫ ОБРАБОТКИ (можно менять)
# =============================================
TARGET_SIZE = (480, 800)  # Целевой размер (ширина, высота)
JPEG_QUALITY = 95  # Качество JPEG (1-100)
BACKGROUND_COLOR = (0, 0, 0)  # Цвет фона - ЧЁРНЫЙ (0, 0, 0)

# =============================================
# ПОДДЕРЖКА ДОПОЛНИТЕЛЬНЫХ ФОРМАТОВ
# =============================================

# Поддержка HEIF/HEIC (форматы iPhone)
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HAS_HEIF = True
except ImportError:
    HAS_HEIF = False
    print("ℹ️  Предупреждение: библиотека pillow-heif не установлена. HEIF/HEIC не будут поддерживаться.")
    print("   Установите: pip install pillow-heif")
except Exception as e:
    HAS_HEIF = False
    print(f"⚠️  Предупреждение: не удалось инициализировать поддержку HEIF: {e}")

# Поддержка RAW файлов (CR2, NEF и др.)
try:
    import rawpy

    HAS_RAW = True
except ImportError:
    HAS_RAW = False
    print("ℹ️  Предупреждение: библиотека rawpy не установлена. RAW файлы (CR2, NEF и др.) не будут поддерживаться.")
    print("   Установите: pip install rawpy")
    print("   Дополнительно на Windows может потребоваться установить Microsoft Visual C++ Redistributable")


def get_supported_formats():
    """Возвращает список поддерживаемых форматов"""
    base_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp', '.gif')
    heif_formats = ()
    raw_formats = ()

    if HAS_HEIF:
        heif_formats = ('.heif', '.heic', '.hif')

    if HAS_RAW:
        raw_formats = ('.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.orf', '.rw2')

    return base_formats + heif_formats + raw_formats


def process_raw_image(input_path):
    """Обрабатывает RAW файл и возвращает PIL Image"""
    try:
        # Открываем RAW файл с rawpy
        with rawpy.imread(input_path) as raw:
            # Конвертируем RAW в RGB
            rgb = raw.postprocess(
                use_camera_wb=True,  # Использовать баланс белого камеры
                half_size=False,  # Полный размер
                no_auto_bright=False,  # Автояркость
                output_bps=8,  # 8 бит на канал
                output_color=rawpy.ColorSpace.sRGB,  # Цветовое пространство sRGB
                gamma=(2.222, 4.5),  # Стандартная гамма
                user_black=None,  # Автоопределение чёрной точки
                user_sat=None,  # Автонасыщенность
                no_auto_scale=False,  # Автомасштабирование
                demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD  # Алгоритм демозаикинга
            )

        # Конвертируем numpy array в PIL Image
        img = Image.fromarray(rgb)
        return img

    except Exception as e:
        print(f"❌ Ошибка при обработке RAW файла {os.path.basename(input_path)}: {e}")
        raise


def check_directories():
    """Проверяет существование папок и создаёт при необходимости"""
    if not os.path.exists(INPUT_DIRECTORY):
        print(f"❌ ОШИБКА: Входная папка не существует!")
        print(f"   Путь: {INPUT_DIRECTORY}")
        print("\nВозможные решения:")
        print("1. Создайте папку в указанном месте")
        print("2. Измените путь в настройках скрипта (переменная INPUT_DIRECTORY)")
        return False

    # Создаём выходную папку если её нет
    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)

    print(f"✅ Входная папка: {INPUT_DIRECTORY}")
    print(f"✅ Выходная папка: {OUTPUT_DIRECTORY}")
    return True


def process_image(input_path, output_path, crop_mode=False):
    """Обрабатывает одно изображение"""
    try:
        # Определяем формат файла
        _, ext = os.path.splitext(input_path)
        ext_lower = ext.lower()

        # Обрабатываем RAW файлы отдельно
        if HAS_RAW and ext_lower in ('.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.orf', '.rw2'):
            img = process_raw_image(input_path)
        else:
            # Открываем обычные форматы
            img = Image.open(input_path)

        # Конвертируем в RGB (если CMYK, градации серого и т.д.)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Создаем ЧЁРНЫЙ фон для прозрачных изображений
            rgb_img = Image.new('RGB', img.size, BACKGROUND_COLOR)
            if img.mode == 'P':
                img = img.convert('RGBA')
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        if crop_mode:
            # Режим обрезки (сохраняет центральную часть)
            # Изменяем размер так, чтобы одна из сторон была не меньше нужной
            img.thumbnail((TARGET_SIZE[0] * 2, TARGET_SIZE[1] * 2), Image.Resampling.LANCZOS)

            # Обрезаем до центра
            left = max(0, (img.width - TARGET_SIZE[0]) // 2)
            top = max(0, (img.height - TARGET_SIZE[1]) // 2)
            right = min(img.width, left + TARGET_SIZE[0])
            bottom = min(img.height, top + TARGET_SIZE[1])

            img = img.crop((left, top, right, bottom))

            # Если изображение меньше целевого размера, увеличиваем
            if img.size != TARGET_SIZE:
                img = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)

            new_img = img
        else:
            # Режим с добавлением ЧЁРНОГО фона (сохраняет пропорции)
            img.thumbnail(TARGET_SIZE, Image.Resampling.LANCZOS)

            # Создаем новое изображение нужного размера с ЧЁРНЫМ фоном
            new_img = Image.new('RGB', TARGET_SIZE, BACKGROUND_COLOR)

            # Вставляем изображение по центру
            offset = (
                (TARGET_SIZE[0] - img.size[0]) // 2,
                (TARGET_SIZE[1] - img.size[1]) // 2
            )
            new_img.paste(img, offset)

        # Сохраняем в JPEG без progressive
        new_img.save(output_path, 'JPEG', quality=JPEG_QUALITY, optimize=True, progressive=False)

        return True

    except Exception as e:
        print(f"❌ Ошибка при обработке {os.path.basename(input_path)}: {e}")
        return False


def process_directory(overwrite=False, crop_mode=False):
    """Обрабатывает все изображения в директории"""
    # Проверяем папки
    if not check_directories():
        return

    # Получаем поддерживаемые форматы
    supported_formats = get_supported_formats()

    print(f"\n📁 Анализ папок...")
    print(f"   Поддерживаемые форматы: {', '.join(supported_formats)}")

    # Выводим информацию о поддерживаемых форматах
    if HAS_HEIF:
        print(f"   ✅ HEIF/HEIC: ПОДДЕРЖИВАЕТСЯ")
    else:
        print(f"   ⚠️  HEIF/HEIC: НЕ ПОДДЕРЖИВАЕТСЯ (установите pillow-heif)")

    if HAS_RAW:
        print(f"   ✅ RAW файлы (CR2, NEF и др.): ПОДДЕРЖИВАЕТСЯ")
    else:
        print(f"   ⚠️  RAW файлы: НЕ ПОДДЕРЖИВАЕТСЯ (установите rawpy)")

    # Получаем список файлов
    files = os.listdir(INPUT_DIRECTORY)
    image_files = []

    for filename in files:
        _, ext = os.path.splitext(filename)
        if ext.lower() in supported_formats:
            image_files.append(filename)

    if not image_files:
        print(f"\n⚠️  В папке {INPUT_DIRECTORY} не найдено поддерживаемых изображений!")
        return

    print(f"\n📊 Найдено изображений: {len(image_files)}")
    print(f"   Целевой размер: {TARGET_SIZE[0]}×{TARGET_SIZE[1]} пикселей")
    print(f"   Цвет фона: ЧЁРНЫЙ (RGB{BACKGROUND_COLOR})")
    print(f"   Режим: {'Обрезка' if crop_mode else 'С добавлением ЧЁРНОГО фона'}")
    print("-" * 60)

    # Счетчики
    processed = 0
    skipped = 0
    failed = 0

    # Обрабатываем изображения
    for i, filename in enumerate(image_files, 1):
        input_path = os.path.join(INPUT_DIRECTORY, filename)

        # Создаем имя выходного файла
        name_without_ext = os.path.splitext(filename)[0]
        output_filename = f"{name_without_ext}.jpg"
        output_path = os.path.join(OUTPUT_DIRECTORY, output_filename)

        # Проверяем, существует ли уже файл
        if os.path.exists(output_path) and not overwrite:
            print(f"⏭️  [{i}/{len(image_files)}] Пропущено (уже существует): {filename}")
            skipped += 1
            continue

        # Обрабатываем изображение
        if process_image(input_path, output_path, crop_mode):
            processed += 1
            print(f"✅ [{i}/{len(image_files)}] Обработано: {filename}")
        else:
            failed += 1
            print(f"❌ [{i}/{len(image_files)}] Ошибка: {filename}")

    # Итог
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ОБРАБОТКИ:")
    print("=" * 60)
    print(f"✅ Успешно обработано: {processed}")
    print(f"⏭️  Пропущено (уже существуют): {skipped}")
    print(f"❌ Не удалось обработать: {failed}")
    print(f"📂 Выходная папка: {OUTPUT_DIRECTORY}")

    if processed > 0:
        print("\n🎉 Обработка завершена успешно!")
        print(f"Все изображения теперь имеют ЧЁРНЫЙ фон")
    else:
        print("\nℹ️  Ничего не обработано. Проверьте настройки путей.")


def show_settings():
    """Показывает текущие настройки"""
    print("\n" + "=" * 60)
    print("⚙️  ТЕКУЩИЕ НАСТРОЙКИ:")
    print("=" * 60)
    print(f"Входная папка: {INPUT_DIRECTORY}")
    print(f"Выходная папка: {OUTPUT_DIRECTORY}")
    print(f"Целевой размер: {TARGET_SIZE[0]}×{TARGET_SIZE[1]}")
    print(f"Качество JPEG: {JPEG_QUALITY}%")
    print(f"Цвет фона: ЧЁРНЫЙ (RGB{BACKGROUND_COLOR})")
    print(f"Поддержка HEIF: {'✅' if HAS_HEIF else '❌ (установите pillow-heif)'}")
    print(f"Поддержка RAW: {'✅' if HAS_RAW else '❌ (установите rawpy)'}")
    print("=" * 60)


def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(
        description='Конвертер изображений в формат 800×480 JPEG с ЧЁРНЫМ фоном',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f'''
Примеры использования:
  %(prog)s                    # Обычная обработка с ЧЁРНЫМ фоном
  %(prog)s --overwrite        # Перезаписать существующие файлы
  %(prog)s --crop             # Режим обрезки (без добавления фона)
  %(prog)s --settings         # Показать настройки и выйти
  %(prog)s --overwrite --crop # Перезаписать в режиме обрезки

Поддерживаемые RAW форматы:
  CR2, CR3 (Canon), NEF (Nikon), ARW (Sony), DNG (Adobe), 
  RAF (Fujifilm), ORF (Olympus), RW2 (Panasonic)

Требуемые библиотеки:
  • pillow-heif для HEIF/HEIC
  • rawpy для RAW файлов

Примечание: По умолчанию используется ЧЁРНЫЙ фон (0, 0, 0)
        '''
    )

    parser.add_argument('--overwrite', '-o', action='store_true',
                        help='Перезаписать существующие файлы')
    parser.add_argument('--crop', '-c', action='store_true',
                        help='Режим обрезки (по умолчанию - с добавлением ЧЁРНОГО фона)')
    parser.add_argument('--settings', '-s', action='store_true',
                        help='Показать текущие настройки и выйти')

    args = parser.parse_args()

    print("🖼️  Конвертер изображений v3.0")
    print("🎨 Цвет фона: ЧЁРНЫЙ")
    print("📸 Поддержка: CR2, NEF, ARW и др. RAW форматы")
    print("=" * 60)

    if args.settings:
        show_settings()
        return

    print("Перед началом проверьте настройки путей в скрипте:")
    print(f"  Входная папка: {INPUT_DIRECTORY}")
    print(f"  Выходная папка: {OUTPUT_DIRECTORY}")

    # Проверяем существование входной папки
    if not os.path.exists(INPUT_DIRECTORY):
        print(f"\n❌ ОШИБКА: Входная папка не существует!")
        print(f"   Путь: {INPUT_DIRECTORY}")
        print("\nИзмените путь в настройках скрипта:")
        print("1. Откройте файл скрипта в текстовом редакторе")
        print("2. Найдите строки с INPUT_DIRECTORY и OUTPUT_DIRECTORY")
        print("3. Укажите правильные пути к вашим папкам")
        input("\nНажмите Enter для выхода...")
        return

    # Предупреждение о перезаписи
    if args.overwrite:
        print("\n⚠️  ВКЛЮЧЁН РЕЖИМ ПЕРЕЗАПИСИ! Существующие файлы будут перезаписаны.")

    if args.crop:
        print("\nℹ️  Режим: ОБРЕЗКА (изображения будут обрезаны до 800×480)")
    else:
        print(f"\nℹ️  Режим: С ЧЁРНЫМ ФОНОМ (изображения сохранят пропорции на чёрном фоне)")

    # Запускаем обработку
    process_directory(args.overwrite, args.crop)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        print("Проверьте настройки и попробуйте снова.")

    input("\nНажмите Enter для выхода...")
