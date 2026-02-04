"""
Unit tests for the Localized type.
"""

from provisioning_station.services.localized import Localized


class TestLocalizedInit:
    """Tests for Localized initialization."""

    def test_empty_init(self):
        """Initialize empty Localized."""
        loc = Localized()
        assert loc.to_dict() == {}
        assert loc.languages == []

    def test_init_with_values(self):
        """Initialize with values dict."""
        loc = Localized({"en": "Hello", "zh": "你好"})
        assert loc.get("en") == "Hello"
        assert loc.get("zh") == "你好"

    def test_init_with_none(self):
        """Initialize with None creates empty."""
        loc = Localized(None)
        assert loc.to_dict() == {}


class TestLocalizedGet:
    """Tests for Localized.get() method."""

    def test_get_existing_lang(self):
        """Get value for existing language."""
        loc = Localized({"en": "Hello", "zh": "你好"})
        assert loc.get("en") == "Hello"
        assert loc.get("zh") == "你好"

    def test_get_missing_lang_with_fallback(self):
        """Get missing language falls back to default (en)."""
        loc = Localized({"en": "Hello"})
        assert loc.get("zh") == "Hello"  # Falls back to "en"

    def test_get_missing_lang_custom_fallback(self):
        """Get missing language with custom fallback."""
        loc = Localized({"zh": "你好", "ja": "こんにちは"})
        assert loc.get("en", fallback="zh") == "你好"

    def test_get_all_missing(self):
        """Get when both target and fallback missing."""
        loc = Localized({"ja": "こんにちは"})
        assert loc.get("fr") is None  # No "fr", no "en"

    def test_get_empty_string(self):
        """Empty string is a valid value (not falsy in language context)."""
        loc = Localized({"en": "", "zh": "你好"})
        # Empty string should be returned, not fallback
        assert loc.get("en") == ""


class TestLocalizedSet:
    """Tests for Localized.set() method."""

    def test_set_new_lang(self):
        """Set value for new language."""
        loc = Localized({"en": "Hello"})
        loc.set("zh", "你好")
        assert loc.get("zh") == "你好"
        assert "zh" in loc.languages

    def test_set_overwrites_existing(self):
        """Set overwrites existing value."""
        loc = Localized({"en": "Hello"})
        loc.set("en", "Hi")
        assert loc.get("en") == "Hi"


class TestLocalizedHas:
    """Tests for Localized.has() method."""

    def test_has_existing(self):
        """has() returns True for existing language."""
        loc = Localized({"en": "Hello"})
        assert loc.has("en") is True

    def test_has_missing(self):
        """has() returns False for missing language."""
        loc = Localized({"en": "Hello"})
        assert loc.has("zh") is False

    def test_has_none_value(self):
        """has() returns False if value is None."""
        loc = Localized({"en": None})
        assert loc.has("en") is False


class TestLocalizedLanguages:
    """Tests for Localized.languages property."""

    def test_languages_empty(self):
        """languages returns empty list when empty."""
        loc = Localized()
        assert loc.languages == []

    def test_languages_multiple(self):
        """languages returns all language codes."""
        loc = Localized({"en": "Hello", "zh": "你好", "ja": "こんにちは"})
        langs = loc.languages
        assert len(langs) == 3
        assert set(langs) == {"en", "zh", "ja"}


class TestLocalizedSerialization:
    """Tests for Localized serialization methods."""

    def test_to_dict(self):
        """to_dict() returns a copy of values."""
        original = {"en": "Hello", "zh": "你好"}
        loc = Localized(original)
        result = loc.to_dict()
        assert result == original
        # Should be a copy
        result["fr"] = "Bonjour"
        assert "fr" not in loc.to_dict()

    def test_from_dict(self):
        """from_dict() creates Localized from dict."""
        data = {"en": "Hello", "zh": "你好"}
        loc = Localized.from_dict(data)
        assert loc.get("en") == "Hello"
        assert loc.get("zh") == "你好"

    def test_from_value(self):
        """from_value() creates Localized with single language."""
        loc = Localized.from_value("Hello", "en")
        assert loc.get("en") == "Hello"
        assert loc.languages == ["en"]

    def test_from_value_default_lang(self):
        """from_value() defaults to 'en' language."""
        loc = Localized.from_value("Hello")
        assert loc.get("en") == "Hello"


class TestLocalizedCompatibility:
    """Tests for compatibility properties."""

    def test_en_property(self):
        """en property returns English value."""
        loc = Localized({"en": "Hello", "zh": "你好"})
        assert loc.en == "Hello"

    def test_zh_property(self):
        """zh property returns Chinese value."""
        loc = Localized({"en": "Hello", "zh": "你好"})
        assert loc.zh == "你好"

    def test_en_property_missing(self):
        """en property returns None when missing."""
        loc = Localized({"zh": "你好"})
        assert loc.en is None

    def test_zh_property_missing(self):
        """zh property returns None when missing."""
        loc = Localized({"en": "Hello"})
        assert loc.zh is None


class TestLocalizedMagicMethods:
    """Tests for Localized magic methods."""

    def test_repr(self):
        """__repr__ shows values."""
        loc = Localized({"en": "Hello"})
        assert "Hello" in repr(loc)
        assert "Localized" in repr(loc)

    def test_eq_same(self):
        """__eq__ compares equal Localized."""
        loc1 = Localized({"en": "Hello"})
        loc2 = Localized({"en": "Hello"})
        assert loc1 == loc2

    def test_eq_different(self):
        """__eq__ compares different Localized."""
        loc1 = Localized({"en": "Hello"})
        loc2 = Localized({"en": "Hi"})
        assert loc1 != loc2

    def test_eq_non_localized(self):
        """__eq__ returns False for non-Localized."""
        loc = Localized({"en": "Hello"})
        assert loc != {"en": "Hello"}
        assert loc != "Hello"

    def test_bool_true(self):
        """__bool__ returns True when has values."""
        loc = Localized({"en": "Hello"})
        assert bool(loc) is True

    def test_bool_false_empty(self):
        """__bool__ returns False when empty."""
        loc = Localized()
        assert bool(loc) is False

    def test_bool_false_all_none(self):
        """__bool__ returns False when all values are None."""
        loc = Localized({"en": None, "zh": None})
        assert bool(loc) is False


class TestLocalizedWithListValues:
    """Tests for Localized with list values (for wiring steps)."""

    def test_list_values(self):
        """Localized can store list values."""
        loc = Localized({
            "en": ["Connect cable", "Power on"],
            "zh": ["连接线缆", "通电"],
        })
        assert loc.get("en") == ["Connect cable", "Power on"]
        assert loc.get("zh") == ["连接线缆", "通电"]

    def test_list_fallback(self):
        """List value fallback works."""
        loc = Localized({
            "en": ["Connect cable", "Power on"],
        })
        result = loc.get("zh")  # Falls back to en
        assert result == ["Connect cable", "Power on"]

    def test_list_set(self):
        """Set list value."""
        loc = Localized()
        loc.set("en", ["Step 1", "Step 2"])
        assert loc.get("en") == ["Step 1", "Step 2"]


class TestLocalizedMultiLanguage:
    """Tests for multiple language support beyond en/zh."""

    def test_three_languages(self):
        """Support three or more languages."""
        loc = Localized({
            "en": "Hello",
            "zh": "你好",
            "ja": "こんにちは",
            "fr": "Bonjour",
        })
        assert loc.get("ja") == "こんにちは"
        assert loc.get("fr") == "Bonjour"
        assert len(loc.languages) == 4

    def test_fallback_chain(self):
        """Fallback to specified language when target missing."""
        loc = Localized({"zh": "你好"})
        # Japanese not present, fallback to zh
        assert loc.get("ja", fallback="zh") == "你好"
