import logging

from PIL import Image, ImageOps

# dHash dimensions: 9 columns x 8 rows produce 8 differences per row across 8 rows = 64 bits
DHASH_WIDTH = 9
DHASH_HEIGHT = 8
DHASH_BITS = (DHASH_WIDTH - 1) * DHASH_HEIGHT  # 64
ALL_ZEROS_HASH = 0
ALL_ONES_HASH = (1 << DHASH_BITS) - 1


def compute_phash(img: Image.Image) -> str | None:
    """Computes a 64-bit difference hash (dHash) for an opened Pillow Image.

    Steps:
    1. Normalizes orientation using ImageOps.exif_transpose (so rotation EXIF tags
       do not prevent matching duplicate photos).
    2. Converts to grayscale ('L').
    3. Resizes to 9x8 pixels (using LANCZOS resampling).
    4. Computes row-wise adjacent pixel differences (pixel[x] > pixel[x+1]).
    5. Discards uniform solid-color images (all 0s or all 1s), returning None to prevent
       spurious distance-0 pairings across unrelated blank/solid images.
    6. Swallows any internal decode/conversion exceptions and returns None so that
       phash failures never impact the caller's corrupt-file sanity check.

    Returns:
        16-character hexadecimal string (e.g. 'a1b2c3d4e5f60718') or None.
    """
    if img is None:
        return None

    try:
        # Normalize orientation using EXIF tags if present
        transposed = ImageOps.exif_transpose(img)
        target_img = transposed if transposed is not None else img

        # Convert to grayscale
        gray = target_img.convert("L")

        # Resize to 9x8 for difference hash
        resized = gray.resize((DHASH_WIDTH, DHASH_HEIGHT), Image.Resampling.LANCZOS)
        pixels = resized.tobytes()

        # Calculate row-wise pixel differences
        hash_int = 0
        for y in range(DHASH_HEIGHT):
            row_offset = y * DHASH_WIDTH
            for x in range(DHASH_WIDTH - 1):
                left = pixels[row_offset + x]
                right = pixels[row_offset + x + 1]
                bit = 1 if left > right else 0
                hash_int = (hash_int << 1) | bit

        # Filter out solid/uniform images (all zeros or all ones)
        if hash_int == ALL_ZEROS_HASH or hash_int == ALL_ONES_HASH:
            return None

        return f"{hash_int:016x}"
    except Exception as e:
        logging.debug(f"Failed to compute perceptual hash: {e}")
        return None


def hamming_distance(hex_a: str | None, hex_b: str | None) -> int:
    """Computes the Hamming distance (number of bit differences) between two 64-bit hex hashes.

    If either hash is None, invalid, or length mismatch, returns 64 (maximum distance).
    """
    if not hex_a or not hex_b:
        return DHASH_BITS

    try:
        val_a = int(hex_a, 16)
        val_b = int(hex_b, 16)
        return (val_a ^ val_b).bit_count()
    except (ValueError, TypeError):
        return DHASH_BITS
