# -*- coding: utf-8 -*-
"""
make_placeholder_icon.py — генератор временной иконки приложения.

ВНИМАНИЕ: это ЗАГЛУШКА, а не фирменная иконка. Скрипт рисует простой
значок светильника со световым конусом и сохраняет его в формате .ico
(размеры 16, 32, 48 и 256 пикселей, 32 бита с прозрачностью).

Иконка используется для:
  * самого IES_Generator.exe (PyInstaller, ключ --icon);
  * установщика «IES Generator Setup.exe» (Inno Setup, SetupIconFile);
  * ярлыков в меню «Пуск» и на рабочем столе (они берут иконку из .exe).

Как заменить на настоящую иконку: положите свой файл в installer/icon.ico
(тот же путь и имя) — сборка подхватит его автоматически, запускать этот
скрипт больше не нужно. Годится любой .ico с набором размеров до 256 px.

Запуск вручную:  python installer/make_placeholder_icon.py
"""

import argparse
import os
import struct

SIZES = (16, 32, 48, 256)

# Палитра значка
BACKGROUND = (0x1B, 0x2A, 0x4A)   # тёмно-синий фон плитки
HOUSING = (0xE8, 0xEA, 0xF0)      # корпус светильника
STEM = (0x9A, 0xA3, 0xB5)         # подвес
LIGHT = (0xFF, 0xC2, 0x4A)        # световой поток

# Геометрия в долях от размера значка
TILE_MARGIN = 0.06
TILE_RADIUS = 0.20
HOUSING_TOP, HOUSING_BOTTOM = 0.22, 0.32
HOUSING_LEFT, HOUSING_RIGHT = 0.22, 0.78
CONE_BOTTOM = 0.80
CONE_HALF_TOP, CONE_HALF_BOTTOM = 0.28, 0.46


def _inside_rounded_tile(u, v):
    """Точка внутри скруглённого квадрата подложки?"""
    lo, hi = TILE_MARGIN, 1.0 - TILE_MARGIN
    if u < lo or u > hi or v < lo or v > hi:
        return False
    r = TILE_RADIUS
    cx = min(max(u, lo + r), hi - r)
    cy = min(max(v, lo + r), hi - r)
    return (u - cx) ** 2 + (v - cy) ** 2 <= r * r


def _blend(base, top, alpha):
    return tuple(int(round(b + (t - b) * alpha)) for b, t in zip(base, top))


def _sample(u, v):
    """Цвет RGBA в точке (u, v), обе координаты в диапазоне 0…1."""
    if not _inside_rounded_tile(u, v):
        return (0, 0, 0, 0)

    color = BACKGROUND

    # Световой конус: расширяется книзу и постепенно гаснет.
    if HOUSING_BOTTOM <= v <= CONE_BOTTOM:
        t = (v - HOUSING_BOTTOM) / (CONE_BOTTOM - HOUSING_BOTTOM)
        half = CONE_HALF_TOP + t * (CONE_HALF_BOTTOM - CONE_HALF_TOP)
        offset = abs(u - 0.5)
        if offset <= half:
            alpha = 0.90 - 0.75 * t
            # смягчаем боковые границы конуса
            alpha *= min(1.0, (half - offset) / half * 6.0)
            color = _blend(color, LIGHT, alpha)

    # Подвес над корпусом.
    if 0.14 <= v < HOUSING_TOP and 0.46 <= u <= 0.54:
        color = STEM

    # Корпус светильника.
    if HOUSING_TOP <= v <= HOUSING_BOTTOM and HOUSING_LEFT <= u <= HOUSING_RIGHT:
        color = HOUSING

    return color + (255,)


def render(size, supersample=4):
    """Отрисовать значок заданного размера. Возвращает строки пикселей RGBA."""
    rows = []
    step = 1.0 / (size * supersample)
    for py in range(size):
        row = []
        for px in range(size):
            r = g = b = a = 0.0
            for sy in range(supersample):
                for sx in range(supersample):
                    u = (px * supersample + sx + 0.5) * step
                    v = (py * supersample + sy + 0.5) * step
                    sr, sg, sb, sa = _sample(u, v)
                    weight = sa / 255.0
                    r += sr * weight
                    g += sg * weight
                    b += sb * weight
                    a += sa
            n = supersample * supersample
            covered = a / 255.0
            if covered <= 0:
                row.append((0, 0, 0, 0))
            else:
                row.append((
                    int(round(r / covered)),
                    int(round(g / covered)),
                    int(round(b / covered)),
                    int(round(a / n)),
                ))
        rows.append(row)
    return rows


def _dib_image(size, rows):
    """Один кадр значка в формате DIB (BITMAPINFOHEADER + BGRA + маска)."""
    header = struct.pack(
        "<IiiHHIIiiII",
        40,              # biSize
        size,            # biWidth
        size * 2,        # biHeight — удвоенная: изображение + маска
        1,               # biPlanes
        32,              # biBitCount
        0,               # biCompression — BI_RGB
        size * size * 4, # biSizeImage
        0, 0, 0, 0,      # разрешение и палитра не используются
    )

    pixels = bytearray()
    for y in range(size - 1, -1, -1):  # строки DIB идут снизу вверх
        for r, g, b, a in rows[y]:
            pixels += bytes((b, g, r, a))

    # Прозрачность задана альфа-каналом, поэтому маска нулевая.
    mask_row = ((size + 31) // 32) * 4
    return header + bytes(pixels) + bytes(mask_row * size)


def build_ico(sizes=SIZES):
    images = [_dib_image(size, render(size)) for size in sizes]

    out = bytearray(struct.pack("<HHH", 0, 1, len(images)))  # ICONDIR
    offset = 6 + 16 * len(images)
    for size, data in zip(sizes, images):
        out += struct.pack(
            "<BBBBHHII",
            size if size < 256 else 0,   # 256 записывается нулём
            size if size < 256 else 0,
            0, 0, 1, 32,
            len(data),
            offset,
        )
        offset += len(data)
    for data in images:
        out += data
    return bytes(out)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=os.path.join(here, "icon.ico"),
                        help="куда записать .ico (по умолчанию installer/icon.ico)")
    parser.add_argument("--force", action="store_true",
                        help="перезаписать существующий файл")
    args = parser.parse_args()

    if os.path.exists(args.out) and not args.force:
        print("Иконка уже существует, оставляю как есть: %s" % args.out)
        return

    data = build_ico()
    with open(args.out, "wb") as f:
        f.write(data)
    print("Записана иконка-заглушка: %s (%d байт, размеры: %s)"
          % (args.out, len(data), ", ".join(str(s) for s in SIZES)))


if __name__ == "__main__":
    main()
