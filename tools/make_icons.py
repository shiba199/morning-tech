# -*- coding: utf-8 -*-
"""
朝刊テック - ステップ8: PWAアイコン生成（標準ライブラリのみ・追加依存なし）

Pillow等を使わず、zlib+struct で PNG を直接書き出して、ブランド配色（朝焼けの
オレンジ＋朝日）のアプリアイコンを生成する。デザイン見本のマーク 🌅 と同系統。

生成物（web/icons/ に出力）:
  icon-512.png        … PWA用（maskable/any）
  icon-192.png        … PWA用
  apple-touch-icon.png… iOSホーム画面用（180px）
  favicon-32.png      … タブのファビコン

実行: .venv/Scripts/python.exe tools/make_icons.py
   （アイコンのデザインを変えたいときに再実行する。通常運用では実行不要）
"""

import math
import os
import struct
import zlib

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "icons")

# ブランド配色（HTMLの --sun2 / --sun1 / 朝日の白に対応）
TOP = (255, 177, 74)    # #FFB14A
BOTTOM = (255, 106, 61)  # #FF6A3D
SUN = (255, 248, 225)    # #FFF8E1


def _lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def _smoothstep(edge0, edge1, x):
    if edge1 == edge0:
        return 0.0 if x < edge0 else 1.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3 - 2 * t)


def _pixel(x, y, s):
    """座標(x,y)・サイズsのRGBA(0-255)を返す。背景=斜めグラデ＋中央やや上に朝日。"""
    # 背景: 左上→右下のグラデーション
    t = (x + y) / (2 * (s - 1))
    r, g, b = _lerp(TOP, BOTTOM, t)

    # 朝日（中央やや上）
    cx, cy = s * 0.5, s * 0.44
    radius = s * 0.24
    d = math.hypot(x - cx, y - cy)

    # 太陽の本体（縁を少しぼかす）
    core = 1.0 - _smoothstep(radius * 0.9, radius, d)
    # 外側のやわらかい光輪
    glow = (1.0 - _smoothstep(radius, radius * 1.6, d)) * 0.35

    mix = max(core, glow)
    if mix > 0:
        r = int(round(r + (SUN[0] - r) * mix))
        g = int(round(g + (SUN[1] - g) * mix))
        b = int(round(b + (SUN[2] - b) * mix))

    # 水平線（朝日の下に細い反射の帯）
    horizon = s * 0.62
    if abs(y - horizon) < max(1, s * 0.012):
        r = min(255, r + 30)
        g = min(255, g + 24)
        b = min(255, b + 16)

    return (r, g, b, 255)


def _write_png(path, size):
    stride = size * 4
    raw = bytearray()
    for y in range(size):
        raw.append(0)  # 各行の先頭にフィルタタイプ0
        for x in range(size):
            raw.extend(_pixel(x, y, size))
    compressed = zlib.compress(bytes(raw), 9)

    def chunk(typ, data):
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # 8bit RGBA
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", compressed)
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    targets = {
        "icon-512.png": 512,
        "icon-192.png": 192,
        "apple-touch-icon.png": 180,
        "favicon-32.png": 32,
    }
    for name, size in targets.items():
        _write_png(os.path.join(OUT_DIR, name), size)
        print(f"生成: {name} ({size}x{size})")
    print(f"出力先: {OUT_DIR}")


if __name__ == "__main__":
    main()
