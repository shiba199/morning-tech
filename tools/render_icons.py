# -*- coding: utf-8 -*-
"""
朝刊テック - アイコン生成: tools/icon.svg を各サイズのPNGに書き出す

ベクター(SVG)を Microsoft Edge のヘッドレスで大きく(1024px)レンダリングし、
それを Pillow で各サイズ（512/192/180/32）に高品質縮小して web/icons/ に書き出す。
（Edgeのヘッドレスは約500px未満の窓を正しく描けないため、大きく描いてから縮小する。）
デザイン変更は tools/icon.svg を編集して再実行。

実行: .venv/Scripts/python.exe tools/render_icons.py
前提: Windows + Microsoft Edge（標準搭載）+ Pillow（ローカルのアイコン生成用。実行環境には不要）。
"""

import os
import subprocess
import tempfile

from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SVG_PATH = os.path.join(BASE, "tools", "icon.svg")
OUT_DIR = os.path.join(BASE, "web", "icons")

TARGETS = {
    "icon-512.png": 512,
    "icon-192.png": 192,
    "apple-touch-icon.png": 180,
    "favicon-32.png": 32,
}

EDGE_CANDIDATES = [
    os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
    os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
]


def find_edge():
    for p in EDGE_CANDIDATES:
        if os.path.isfile(p):
            return p
    raise SystemExit("Microsoft Edge が見つかりません。Edgeのパスを確認してください。")


def main():
    edge = find_edge()
    with open(SVG_PATH, "r", encoding="utf-8") as f:
        svg = f.read()

    # SVGをビューポートいっぱいに表示するHTMLでラップ（余白なしで正方形に切り出すため）
    html = ("<!doctype html><meta charset=utf-8>"
            "<style>html,body{margin:0;padding:0;overflow:hidden}"
            "svg{display:block;width:100vw;height:100vh}</style>" + svg)
    tmp = os.path.join(tempfile.gettempdir(), "morning_icon.html")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)

    os.makedirs(OUT_DIR, exist_ok=True)

    # まず大きく(1024px)レンダリング（Edgeは小さい窓を正しく描けないため）
    render = 1024
    big = os.path.join(tempfile.gettempdir(), "morning_icon_1024.png")
    subprocess.run([
        edge, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        f"--screenshot={big}", f"--window-size={render},{render}",
        "file:///" + tmp.replace("\\", "/"),
    ], check=True, capture_output=True)

    # Pillow で各サイズへ高品質縮小
    src = Image.open(big).convert("RGBA")
    for name, size in TARGETS.items():
        img = src.resize((size, size), Image.LANCZOS)
        img.save(os.path.join(OUT_DIR, name))
        print(f"生成: {name} ({size}x{size})")
    print(f"出力先: {OUT_DIR}")


if __name__ == "__main__":
    main()
