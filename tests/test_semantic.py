import importlib.util
import os
import socket

import pytest
from test_bank import bank_class


def test_unprovisioned_semantics_is_lexical_with_clear_remediation(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank", semantic_enabled=True)
    bank.remember("Rule", "Keep data local", source="user:1")
    result = bank.search("local")
    assert result["mode"] == "lexical"
    assert result["semantic_status"] == "unavailable"
    assert "install" in result["semantic_reason"].lower()
    assert result["results"]


def test_semantic_install_missing_extra_gives_actionable_error(tmp_path):
    if importlib.util.find_spec("fastembed"):
        pytest.skip("Extra installed in this environment")
    bank = bank_class().initialize(tmp_path / "bank")
    with pytest.raises(ValueError, match="semantic"):
        bank.provision_semantic()


@pytest.mark.semantic
def test_real_local_model_retrieves_paraphrases_without_network(tmp_path, monkeypatch):
    cache = os.environ.get("MAVERICK_TEST_MODEL_CACHE")
    if not cache:
        pytest.skip("Run with an explicitly provisioned MAVERICK_TEST_MODEL_CACHE")
    bank = bank_class().initialize(
        tmp_path / "bank", semantic_enabled=True, semantic_cache_dir=cache
    )
    english = bank.remember(
        "Architecture",
        "Our database runs entirely on this laptop without sending information to external servers.",
        source="test:1",
    )
    russian = bank.remember(
        "Общение", "Пожалуйста, отвечай лаконично и переходи сразу к сути.", source="test:2"
    )
    bank.remember("Other", "Bananas grow in warm tropical climates.", source="test:3")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")

    def no_network(*args, **kwargs):
        raise AssertionError("Semantic serving attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    result = bank.search("offline private storage", limit=1)
    assert result["mode"] == "hybrid", result
    assert result["results"][0]["id"] == english["id"]
    result = bank.search("не люблю длинные объяснения", limit=1)
    assert result["mode"] == "hybrid", result
    assert result["results"][0]["id"] == russian["id"]


def test_model_artifact_resolution_rejects_cache_escape(tmp_path):
    try:
        from maverick_bank.embeddings import model_artifact
    except ImportError:
        pytest.fail("Cache artifact boundary is not implemented")
    cache = tmp_path / "cache"
    model = cache / "snapshot"
    model.mkdir(parents=True)
    file = model / "model.onnx"
    file.write_bytes(b"fixture")
    assert model_artifact(cache, model, "model.onnx") == file
    with pytest.raises(ValueError):
        model_artifact(cache, model, "../../outside")


def test_huggingface_cache_symlinks_are_allowed_only_inside_cache(tmp_path):
    try:
        from maverick_bank.embeddings import model_artifact
    except ImportError:
        pytest.fail("Cache artifact boundary is not implemented")
    cache = tmp_path / "cache"
    model = cache / "snapshot"
    model.mkdir(parents=True)
    blob = cache / "blob"
    blob.write_bytes(b"fixture")
    link = model / "model.onnx"
    try:
        link.symlink_to(blob)
    except OSError:
        pytest.skip("OS denies symlink creation for this account")
    assert model_artifact(cache, model, "model.onnx") == blob
    link.unlink()
    outside = tmp_path / "private"
    outside.write_bytes(b"private")
    link.symlink_to(outside)
    with pytest.raises(ValueError):
        model_artifact(cache, model, "model.onnx")


def test_pinned_fingerprints_include_external_onnx_weights(tmp_path):
    try:
        from maverick_bank.embeddings import model_fingerprints
    except ImportError:
        pytest.fail("Full model artifact pinning is not implemented")
    model = tmp_path / "snapshot"
    model.mkdir()
    (model / "model.onnx").write_bytes(b"graph")
    (model / "model.onnx_data").write_bytes(b"external weights")
    before = model_fingerprints(tmp_path, model)
    assert "model.onnx_data" in before
    (model / "model.onnx_data").write_bytes(b"different weights")
    assert model_fingerprints(tmp_path, model)["model.onnx_data"] != before["model.onnx_data"]
