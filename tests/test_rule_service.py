from datetime import datetime

from services.rule_service import (evaluate_rules, evaluate_single_rule,
                                   match_field, resolve_rule_target_folder)


def test_match_field():
    assert match_field("photo.jpg", "equals", "PHOTO.JPG")
    assert not match_field("photo.jpg", "equals", "photo")
    assert match_field("DCIM_Screenshots", "contains", "Screenshot")
    assert match_field("Sony ILCE-7M4", "startswith", "sony")
    assert match_field("MyFolder", "endswith", "folder")
    assert not match_field(None, "equals", "abc")


def test_evaluate_single_rule_extension():
    ctx = {"extension": ".jpg", "filename": "test.jpg"}

    # Exact match with dot
    rule = {"field": "extension", "value": ".jpg"}
    assert evaluate_single_rule(rule, ctx)

    # Without dot
    rule = {"field": "extension", "value": "jpg"}
    assert evaluate_single_rule(rule, ctx)

    # Comma-separated list
    rule = {"field": "extension", "value": ".png, .jpg, .gif"}
    assert evaluate_single_rule(rule, ctx)

    # Mismatch
    rule = {"field": "extension", "value": ".png"}
    assert not evaluate_single_rule(rule, ctx)


def test_evaluate_single_rule_source_folder():
    ctx = {
        "src_dir": "Screenshots",
        "src_dir_full": "/Users/test/Pictures/Screenshots",
    }

    rule = {"field": "source_folder", "operator": "contains", "value": "Screenshots"}
    assert evaluate_single_rule(rule, ctx)

    rule = {"field": "source_folder", "operator": "equals", "value": "Screenshots"}
    assert evaluate_single_rule(rule, ctx)

    rule = {"field": "source_folder", "operator": "contains", "value": "Pictures"}
    assert evaluate_single_rule(rule, ctx)

    rule = {"field": "source_folder", "operator": "contains", "value": "Camera"}
    assert not evaluate_single_rule(rule, ctx)


def test_evaluate_single_rule_camera_model():
    ctx = {"camera_model": "ILCE-7M4"}

    rule = {"field": "camera_model", "operator": "contains", "value": "7M4"}
    assert evaluate_single_rule(rule, ctx)

    rule = {"field": "camera_model", "operator": "equals", "value": "ilce-7m4"}
    assert evaluate_single_rule(rule, ctx)

    rule = {"field": "camera_model", "operator": "contains", "value": "Canon"}
    assert not evaluate_single_rule(rule, ctx)

    # No camera model in context
    ctx_no_camera = {"camera_model": None}
    assert not evaluate_single_rule(rule, ctx_no_camera)


def test_resolve_rule_target_folder():
    dt = datetime(2026, 6, 15)
    res = resolve_rule_target_folder(
        "Screenshots/{YYYY}/{MM}", dt, "screenshot.png", camera_model=None
    )
    assert res == "Screenshots/2026/06"

    res = resolve_rule_target_folder(
        "Cameras/{camera}", dt, "sample.jpg", camera_model="Canon EOS R5"
    )
    assert res == "Cameras/Canon EOS R5"

    # Directory traversal prevention
    res = resolve_rule_target_folder("../unsafe/folder/../../secret", dt, "sample.jpg")
    assert res == "unsafe/folder/secret"


def test_evaluate_rules_first_match():
    rules = [
        {
            "id": "r1",
            "field": "extension",
            "value": ".png",
            "target_folder": "Screenshots",
        },
        {
            "id": "r2",
            "field": "camera_model",
            "value": "Sony",
            "target_folder": "Sony_Photos",
        },
    ]

    # File matches r1
    ctx1 = {
        "filename": "img.png",
        "extension": ".png",
        "camera_model": "Sony ILCE-7M4",
        "dt": datetime(2026, 6, 1),
    }
    folder, matched = evaluate_rules(rules, ctx1)
    assert folder == "Screenshots"
    assert matched["id"] == "r1"

    # File matches r2
    ctx2 = {
        "filename": "img.jpg",
        "extension": ".jpg",
        "camera_model": "Sony ILCE-7M4",
        "dt": datetime(2026, 6, 1),
    }
    folder, matched = evaluate_rules(rules, ctx2)
    assert folder == "Sony_Photos"
    assert matched["id"] == "r2"

    # File matches no rule
    ctx3 = {
        "filename": "img.jpg",
        "extension": ".jpg",
        "camera_model": "Nikon Z6",
        "dt": datetime(2026, 6, 1),
    }
    folder, matched = evaluate_rules(rules, ctx3)
    assert folder is None
    assert matched is None


def test_evaluate_rules_empty():
    assert evaluate_rules([], {}) == (None, None)
    assert evaluate_rules(None, {}) == (None, None)
