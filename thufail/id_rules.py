import re

PLACEHOLDER_VALUES = {"xxxxx", "x", "xxxx", "xxxxxx", "n/a", "na", "none", ""}


def check_national_id(value, expected_prefix: str = "784", expected_length: int = 15) -> list[str]:
    """Return a list of rule violations for a single national ID value (empty list = valid)."""
    if value is None or (isinstance(value, float) and value != value):  # NaN
        return ["missing"]

    text = str(value).strip()
    if text.lower() in PLACEHOLDER_VALUES:
        return ["placeholder_value"]

    digits_only = re.sub(r"[^0-9]", "", text)
    issues = []

    if not re.fullmatch(r"[0-9-]+", text):
        issues.append("non_numeric_characters")

    if len(digits_only) != expected_length:
        issues.append(f"wrong_length(got {len(digits_only)}, expected {expected_length})")

    if not digits_only.startswith(expected_prefix):
        issues.append(f"wrong_prefix(got '{digits_only[:len(expected_prefix)]}', expected '{expected_prefix}')")

    return issues
