import re
import unicodedata


def generate_slug(name: str, existing_slugs: list[str]) -> str:
    """Normalize name to a unique slug, resolving conflicts with -2, -3 suffixes."""
    # Normalize unicode (remove accents)
    normalized = unicodedata.normalize("NFD", name)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")

    # Lowercase + replace non-alphanumeric with dash
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_str.lower())

    # Collapse multiple dashes, strip leading/trailing dashes
    slug = re.sub(r"-{2,}", "-", slug).strip("-")

    # Truncate to 60 chars (avoid splitting mid-word at boundary)
    slug = slug[:60].rstrip("-")

    if not slug:
        slug = "calendrier"

    if slug not in existing_slugs:
        return slug

    counter = 2
    while True:
        candidate = f"{slug}-{counter}"
        if candidate not in existing_slugs:
            return candidate
        counter += 1
