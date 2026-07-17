import os
from unittest.mock import patch
from urllib.parse import urlencode


def _thumb_url(path, src_dirs):
    params = [("path", path)]
    for d in src_dirs:
        params.append(("src_dir", d))
    return f"/api/thumbnail?{urlencode(params)}"


def test_thumbnail_valid_image_returns_jpeg(
    client, csrf_headers, temp_workspace, image_creator
):
    """A valid image inside an allowed source directory returns a JPEG thumbnail."""
    src = temp_workspace["src"]
    photo_path = os.path.join(src, "photo1.jpg")
    image_creator(photo_path, exif_date_str="2026:06:01 12:00:00")

    response = client.get(
        _thumb_url(photo_path, [src]),
        headers=csrf_headers,
    )

    assert response.status_code == 200
    assert response.mimetype == "image/jpeg"
    # JPEG files start with the SOI marker 0xFFD8
    assert response.data[:2] == b"\xff\xd8"


def test_thumbnail_is_resized_within_bounds(
    client, csrf_headers, temp_workspace, image_creator
):
    """The generated thumbnail must not exceed the configured max dimensions."""
    import io

    from PIL import Image

    src = temp_workspace["src"]
    photo_path = os.path.join(src, "big.jpg")
    os.makedirs(os.path.dirname(photo_path), exist_ok=True)
    Image.new("RGB", (800, 600), color="red").save(photo_path, "JPEG")

    response = client.get(
        _thumb_url(photo_path, [src]),
        headers=csrf_headers,
    )

    assert response.status_code == 200
    thumb = Image.open(io.BytesIO(response.data))
    assert thumb.width <= 150
    assert thumb.height <= 150


def test_thumbnail_converts_non_rgb_mode(client, csrf_headers, temp_workspace):
    """Palette/RGBA source images are converted to RGB before JPEG encoding."""
    from PIL import Image

    src = temp_workspace["src"]
    photo_path = os.path.join(src, "transparent.png")
    os.makedirs(os.path.dirname(photo_path), exist_ok=True)
    Image.new("RGBA", (50, 50), color=(255, 0, 0, 128)).save(photo_path, "PNG")

    response = client.get(
        _thumb_url(photo_path, [src]),
        headers=csrf_headers,
    )

    assert response.status_code == 200
    assert response.mimetype == "image/jpeg"


def test_thumbnail_unexpected_error_returns_500(
    client, csrf_headers, temp_workspace, image_creator
):
    """Unexpected failures during thumbnail generation return 500, not a crash."""
    src = temp_workspace["src"]
    photo_path = os.path.join(src, "photo1.jpg")
    image_creator(photo_path)

    with patch("routes.thumbnail.Image.open", side_effect=OSError("disk error")):
        response = client.get(
            _thumb_url(photo_path, [src]),
            headers=csrf_headers,
        )

    assert response.status_code == 500


def test_thumbnail_path_traversal_rejected(
    client, csrf_headers, temp_workspace, image_creator
):
    """A path outside the declared src_dir(s) must be rejected, even if it's a real image."""
    src = temp_workspace["src"]
    outside_dir = os.path.join(temp_workspace["root"], "outside")
    outside_path = os.path.join(outside_dir, "secret.jpg")
    image_creator(outside_path)

    response = client.get(
        _thumb_url(outside_path, [src]),
        headers=csrf_headers,
    )

    assert response.status_code == 403


def test_thumbnail_traversal_via_dotdot_rejected(
    client, csrf_headers, temp_workspace, image_creator
):
    """A '..'-based traversal attempt out of the allowed directory must be rejected."""
    src = temp_workspace["src"]
    outside_dir = os.path.join(temp_workspace["root"], "outside")
    outside_path = os.path.join(outside_dir, "secret.jpg")
    image_creator(outside_path)

    traversal_path = os.path.join(src, "..", "outside", "secret.jpg")

    response = client.get(
        _thumb_url(traversal_path, [src]),
        headers=csrf_headers,
    )

    assert response.status_code == 403


def test_thumbnail_missing_file(client, csrf_headers, temp_workspace):
    """A well-formed but nonexistent path inside the allowed dir returns 404."""
    src = temp_workspace["src"]
    missing_path = os.path.join(src, "does_not_exist.jpg")

    response = client.get(
        _thumb_url(missing_path, [src]),
        headers=csrf_headers,
    )

    assert response.status_code == 404


def test_thumbnail_corrupt_file_returns_422(client, csrf_headers, temp_workspace):
    """A file with an image extension but invalid/corrupt content is handled gracefully."""
    src = temp_workspace["src"]
    corrupt_path = os.path.join(src, "corrupt.jpg")
    with open(corrupt_path, "wb") as f:
        f.write(b"not a real image")

    response = client.get(
        _thumb_url(corrupt_path, [src]),
        headers=csrf_headers,
    )

    assert response.status_code == 422


def test_thumbnail_unsupported_extension_returns_400(
    client, csrf_headers, temp_workspace
):
    """Files whose extension is not in Config.IMAGE_EXTENSIONS are rejected before any I/O."""
    src = temp_workspace["src"]
    text_path = os.path.join(src, "notes.txt")
    with open(text_path, "wb") as f:
        f.write(b"hello world")

    response = client.get(
        _thumb_url(text_path, [src]),
        headers=csrf_headers,
    )

    assert response.status_code == 400


def test_thumbnail_missing_params_returns_400(client, csrf_headers, temp_workspace):
    """Missing path or src_dir query params return 400."""
    src = temp_workspace["src"]

    response = client.get("/api/thumbnail", headers=csrf_headers)
    assert response.status_code == 400

    response = client.get(
        f"/api/thumbnail?{urlencode([('path', os.path.join(src, 'a.jpg'))])}",
        headers=csrf_headers,
    )
    assert response.status_code == 400


def test_thumbnail_requires_csrf_token(client, temp_workspace, image_creator):
    """Requests without a valid CSRF token are rejected, matching other endpoints."""
    src = temp_workspace["src"]
    photo_path = os.path.join(src, "photo1.jpg")
    image_creator(photo_path)

    response = client.get(_thumb_url(photo_path, [src]))

    assert response.status_code == 403


def test_thumbnail_requires_localhost(
    client, csrf_headers, temp_workspace, image_creator
):
    """Non-localhost requests are rejected, matching /api/select-dir, /api/shutdown, /api/undo."""
    src = temp_workspace["src"]
    photo_path = os.path.join(src, "photo1.jpg")
    image_creator(photo_path)

    response = client.get(
        _thumb_url(photo_path, [src]),
        headers=csrf_headers,
        environ_overrides={"REMOTE_ADDR": "203.0.113.10"},
    )

    assert response.status_code == 403
