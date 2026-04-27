import re

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MARKUP_CHARS = re.compile(r"[<>]")


def sanitize_plain_text(value: str, *, max_length: int, allow_markup: bool) -> str:
    cleaned = CONTROL_CHARS.sub("", value).strip()
    if len(cleaned) > max_length:
        raise ValueError("Input exceeds the maximum allowed length.")
    if not allow_markup and MARKUP_CHARS.search(cleaned):
        raise ValueError("Markup is not allowed in this field.")
    return cleaned
