from app.utils.text import normalize_spaces, slugify_title


def test_normalize_spaces():
    assert normalize_spaces("hello   world") == "hello world"


def test_slugify_title_basic():
    assert slugify_title("Hello World") == "hello-world"


def test_slugify_title_trims_extra_separators():
    assert slugify_title("  Hello   World  ") == "hello-world"


def test_slugify_title_lowercase():
    assert slugify_title("PyThOn ROCKS") == "python-rocks"
