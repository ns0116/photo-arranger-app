import os
import subprocess
from PIL import Image

base_path = 'icon_base.png'

# 1. ICOの作成
print("Creating icon.ico...")
img = Image.open(base_path)
img.save('icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])

# 2. ICNSの作成
print("Creating icon.icns...")
iconset_dir = 'icon.iconset'
os.makedirs(iconset_dir, exist_ok=True)

sizes = [
    (16, '16x16'), (32, '16x16@2x'), (32, '32x32'), (64, '32x32@2x'),
    (128, '128x128'), (256, '128x128@2x'), (256, '256x256'),
    (512, '256x256@2x'), (512, '512x512'), (1024, '512x512@2x')
]

for size, name in sizes:
    output_png = os.path.join(iconset_dir, f'icon_{name}.png')
    # -s format png でPNGに強制変換
    subprocess.run([
        'sips', '-s', 'format', 'png', '-z', str(size), str(size), base_path, '--out', output_png
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# iconutilでicnsに変換
subprocess.run(['iconutil', '-c', 'icns', iconset_dir])

# 中間生成物の削除
for size, name in sizes:
    os.remove(os.path.join(iconset_dir, f'icon_{name}.png'))
os.rmdir(iconset_dir)

print("Icons created successfully.")
