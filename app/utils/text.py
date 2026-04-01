def normalize_spaces(text: str) -> str:
    return " ".join(text.split())


def slugify_title(text: str) -> str:
    return "-".join(text.strip().lower().split())
