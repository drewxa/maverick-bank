import pytest
from test_bank import bank_class


@pytest.mark.parametrize(
    "bad", ["../outside", "/etc/passwd", "C:\\private", "a:b", "..\\outside", "\\\\server\\share"]
)
def test_memory_identifier_cannot_be_a_filesystem_escape(tmp_path, bad):
    bank = bank_class().initialize(tmp_path / "bank")
    with pytest.raises(ValueError):
        bank.read(bad)


def test_symlink_note_is_never_followed(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank")
    outside = tmp_path / "private.md"
    outside.write_text("Private outside content", encoding="utf-8")
    link = bank.root / "notes" / "escape.md"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("OS denies symlink creation for this account")
    assert bank.search("Private")["results"] == []
    assert any(i["code"] == "unsafe_path" for i in bank.audit()["issues"])
