import os
import re
from datetime import datetime


def match_field(field_val, operator, rule_val):
    """Evaluates whether field_val matches rule_val under operator."""
    if field_val is None:
        return False

    val_str = str(field_val).strip()
    rule_str = str(rule_val).strip()

    op = (operator or "").lower()

    if op == "equals":
        return val_str.lower() == rule_str.lower()
    elif op == "startswith":
        return val_str.lower().startswith(rule_str.lower())
    elif op == "endswith":
        return val_str.lower().endswith(rule_str.lower())
    else:  # default is contains
        return rule_str.lower() in val_str.lower()


def evaluate_single_rule(rule, file_context):
    """Checks if a single rule matches the given file context.

    Returns True if matches, False otherwise.
    """
    field = (rule.get("field") or "").lower()
    value = rule.get("value", "")
    operator = rule.get("operator")

    if not field or not value:
        return False

    if field == "extension":
        ext = file_context.get("extension", "").lower()
        # Support comma-separated extension values, e.g. ".jpg, .jpeg" or "jpg, png"
        targets = [t.strip().lower() for t in str(value).split(",") if t.strip()]
        for target in targets:
            if not target.startswith("."):
                target = "." + target
            if ext == target:
                return True
        return False

    elif field == "source_folder":
        # Check against both dirname and full path for flexibility
        src_dir = file_context.get("src_dir", "")
        src_dir_full = file_context.get("src_dir_full", "")
        op = operator or "contains"
        return match_field(src_dir, op, value) or match_field(src_dir_full, op, value)

    elif field == "camera_model":
        model = file_context.get("camera_model")
        if not model:
            return False
        op = operator or "contains"
        return match_field(model, op, value)

    return False


def resolve_rule_target_folder(template_str, dt, filename, camera_model=None):
    """Resolves dynamic tokens inside a rule's target_folder path.

    Supported tokens:
        {YYYY}: 4-digit year
        {MM}: 2-digit month
        {DD}: 2-digit day
        {filename}: original filename without extension
        {ext}: file extension (with dot)
        {camera}: camera model (sanitized)
    """
    if not template_str:
        return ""

    base, ext = os.path.splitext(filename)
    res = template_str

    target_dt = dt or datetime.now()
    res = res.replace("{YYYY-MM-DD}", target_dt.strftime("%Y-%m-%d"))
    res = res.replace("{YYYY-MM}", target_dt.strftime("%Y-%m"))
    res = res.replace("{YYYYMMDD}", target_dt.strftime("%Y%m%d"))
    res = res.replace("{YYYY/MM/DD}", target_dt.strftime("%Y/%m/%d"))
    res = res.replace("{YYYY/MM}", target_dt.strftime("%Y/%m"))
    res = res.replace("{YYYY}", target_dt.strftime("%Y"))
    res = res.replace("{MM}", target_dt.strftime("%m"))
    res = res.replace("{DD}", target_dt.strftime("%d"))

    res = res.replace("{filename}", base)
    res = res.replace("{ext}", ext)

    safe_camera = re.sub(r'[\\/*?:"<>|]', "_", camera_model or "Unknown").strip()
    res = res.replace("{camera}", safe_camera)
    res = res.replace("{camera_model}", safe_camera)

    # Normalize path separators, prevent directory traversal
    parts = [
        p for p in res.replace("\\", "/").split("/") if p and p != "." and p != ".."
    ]
    return "/".join(parts)


def evaluate_rules(rules, file_context):
    """Evaluates rules sequentially against file_context (first match wins).

    file_context expects:
        - filename: str
        - src_dir: str (basename)
        - src_dir_full: str (full directory path)
        - extension: str (e.g. '.jpg')
        - camera_model: str | None
        - dt: datetime | None

    Returns:
        tuple (target_folder: str | None, matched_rule: dict | None)
    """
    if not rules or not isinstance(rules, list):
        return None, None

    for rule in rules:
        if not isinstance(rule, dict):
            continue
        if evaluate_single_rule(rule, file_context):
            target_tmpl = rule.get("target_folder", "").strip()
            if not target_tmpl:
                continue
            resolved_folder = resolve_rule_target_folder(
                target_tmpl,
                file_context.get("dt"),
                file_context.get("filename", ""),
                file_context.get("camera_model"),
            )
            return resolved_folder, rule

    return None, None
