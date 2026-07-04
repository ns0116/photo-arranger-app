import os
import subprocess

from PIL import Image

# 修正 #14: __file__ を基準にプロジェクトルートを特定することで、
# どのディレクトリから実行しても正しいパスで動作するようにする
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)

base_path = os.path.join(_PROJECT_ROOT, "assets", "icon_base.png")
_ico_output = os.path.join(_PROJECT_ROOT, "assets", "icon.ico")
_icns_output = os.path.join(_PROJECT_ROOT, "assets", "icon.icns")
_iconset_dir = os.path.join(_PROJECT_ROOT, "icon.iconset")

# 1. ICOの作成
print("Creating icon.ico...")
img = Image.open(base_path)
img.save(
    _ico_output,
    format="ICO",
    sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
)

# 2. ICNSの作成
print("Creating icon.icns...")
os.makedirs(_iconset_dir, exist_ok=True)

sizes = [
    (16, "16x16"),
    (32, "16x16@2x"),
    (32, "32x32"),
    (64, "32x32@2x"),
    (128, "128x128"),
    (256, "128x128@2x"),
    (256, "256x256"),
    (512, "256x256@2x"),
    (512, "512x512"),
    (1024, "512x512@2x"),
]

for size, name in sizes:
    output_png = os.path.join(_iconset_dir, f"icon_{name}.png")
    subprocess.run(
        [
            "sips",
            "-s",
            "format",
            "png",
            "-z",
            str(size),
            str(size),
            base_path,
            "--out",
            output_png,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

# iconutilでicnsに変換、出力先をassets/icon.icnsに指定
subprocess.run(["iconutil", "-c", "icns", "-o", _icns_output, _iconset_dir])

# 中間生成物の削除
for size, name in sizes:
    os.remove(os.path.join(_iconset_dir, f"icon_{name}.png"))
os.rmdir(_iconset_dir)

print("Icons created successfully.")
