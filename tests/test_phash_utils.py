import io

from PIL import Image, ImageDraw

from utils.phash_utils import compute_phash, hamming_distance


def _create_pattern_image(width=100, height=100, seed_color=0):
    """Creates a non-uniform test image with diagonal stripes / gradients."""
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)
    for i in range(0, max(width, height), 10):
        c = (i * 7 + seed_color) % 255
        draw.line([(0, i), (i, 0)], fill=(c, 255 - c, (c * 2) % 255), width=3)
        draw.rectangle([i, i, i + 5, i + 5], fill=(255 - c, c, 128))
    return img


def test_identical_image_distance_zero():
    img = _create_pattern_image()
    hash1 = compute_phash(img)
    hash2 = compute_phash(img)
    assert hash1 is not None
    assert hash2 is not None
    assert len(hash1) == 16
    assert hash1 == hash2
    assert hamming_distance(hash1, hash2) == 0


def test_resized_and_compressed_image_within_threshold():
    img_orig = _create_pattern_image(width=200, height=200)
    hash_orig = compute_phash(img_orig)

    # Resized version
    img_resized = img_orig.resize((64, 64))
    hash_resized = compute_phash(img_resized)

    # JPEG compressed version
    buf = io.BytesIO()
    img_orig.save(buf, format="JPEG", quality=40)
    buf.seek(0)
    img_jpeg = Image.open(buf)
    hash_jpeg = compute_phash(img_jpeg)

    assert hash_orig is not None
    assert hash_resized is not None
    assert hash_jpeg is not None

    # Both variations should have low Hamming distance (< 5)
    dist_resized = hamming_distance(hash_orig, hash_resized)
    dist_jpeg = hamming_distance(hash_orig, hash_jpeg)

    assert dist_resized <= 5
    assert dist_jpeg <= 5


def test_distinct_images_large_distance():
    img1 = _create_pattern_image(seed_color=10)
    # Distinct image: checkerboard pattern
    img2 = Image.new("RGB", (100, 100), color="white")
    draw = ImageDraw.Draw(img2)
    step = 20
    for y in range(0, 100, step):
        for x in range(0, 100, step):
            if ((x // step) + (y // step)) % 2 == 0:
                draw.rectangle([x, y, x + step, y + step], fill="black")

    hash1 = compute_phash(img1)
    hash2 = compute_phash(img2)

    assert hash1 is not None
    assert hash2 is not None
    assert hamming_distance(hash1, hash2) >= 15


def test_solid_color_returns_none():
    # Solid black
    black = Image.new("RGB", (100, 100), color=(0, 0, 0))
    assert compute_phash(black) is None

    # Solid white
    white = Image.new("RGB", (100, 100), color=(255, 255, 255))
    assert compute_phash(white) is None

    # Solid gray
    gray = Image.new("RGB", (100, 100), color=(128, 128, 128))
    assert compute_phash(gray) is None


def test_none_or_corrupt_image_returns_none():
    assert compute_phash(None) is None


def test_exif_orientation_normalized():
    # Base image
    img = _create_pattern_image(width=120, height=80)
    hash_base = compute_phash(img)

    # When a camera is held vertically, the sensor records rotated 90 CW (ROTATE_90)
    # and attaches EXIF Orientation 6 (indicating the image needs 90 CCW to be normal).
    rotated = img.transpose(Image.Transpose.ROTATE_90)
    exif = rotated.getexif()
    exif[0x0112] = 6  # Orientation: Rotate 90 CW

    # Save with EXIF to bytes and reload
    buf = io.BytesIO()
    rotated.save(buf, format="JPEG", exif=exif)
    buf.seek(0)
    img_with_exif = Image.open(buf)

    hash_rotated_exif = compute_phash(img_with_exif)
    assert hash_rotated_exif is not None
    assert hash_base is not None
    # With exif_transpose, the distance between the two should be within default threshold (<= 5)
    assert hamming_distance(hash_base, hash_rotated_exif) <= 5


def test_hamming_distance_edge_cases():
    assert hamming_distance(None, "0000000000000000") == 64
    assert hamming_distance("0000000000000000", None) == 64
    assert hamming_distance("", "0000000000000000") == 64
    assert hamming_distance("invalid_hex", "0000000000000000") == 64

    # 1 bit difference
    assert hamming_distance("0000000000000000", "0000000000000001") == 1
    # 4 bits difference (f = 1111)
    assert hamming_distance("0000000000000000", "000000000000000f") == 4
    # All 64 bits different
    assert hamming_distance("0000000000000000", "ffffffffffffffff") == 64
