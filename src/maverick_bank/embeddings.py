"""Explicit local model provisioning; serving never downloads or calls an API."""

from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from importlib.metadata import version
from pathlib import Path

from filelock import FileLock

from .notes import digest, utcnow
from .paths import atomic_text, confined


def cache_directory(state: Path, configured: str = "") -> Path:
    return Path(configured).expanduser().resolve() if configured else confined(state, "models")


def _receipt_path(cache: Path, model: str) -> Path:
    return confined(cache, f"receipts/{digest(model.encode())[:24]}.json")


def _text_embedding():
    try:
        from fastembed import TextEmbedding
    except ImportError as exc:
        raise ValueError(
            "Semantic extra is missing. Install maverick-bank[semantic] from the same release source, then run semantic install."
        ) from exc
    return TextEmbedding


def _file_hash(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def model_artifact(cache: Path, model_dir: Path, relative: str) -> Path:
    # Hugging Face snapshots intentionally link to blobs elsewhere inside their cache.
    part = Path(relative)
    if (
        not relative
        or part.is_absolute()
        or ".." in part.parts
        or ":" in relative
        or "\\" in relative
    ):
        raise ValueError("Invalid model artifact path")
    resolved = (model_dir / part).resolve()
    if not resolved.is_relative_to(cache.resolve()):
        raise ValueError("Model artifact escapes the configured cache")
    return resolved


def model_fingerprints(cache: Path, model_dir: Path) -> dict[str, str]:
    return {
        path.relative_to(model_dir).as_posix(): _file_hash(
            model_artifact(cache, model_dir, path.relative_to(model_dir).as_posix())
        )
        for path in sorted(model_dir.rglob("*"))
        if path.is_file()
    }


def provision(state: Path, model: str, configured_cache: str = "") -> dict:
    TextEmbedding = _text_embedding()
    if model not in {item["model"] for item in TextEmbedding.list_supported_models()}:
        raise ValueError(
            "Model is not in the installed FastEmbed registry; choose a supported local ONNX model"
        )
    cache = cache_directory(state, configured_cache)
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    with FileLock(confined(cache, "provision.lock"), timeout=600):
        embedding = TextEmbedding(
            model_name=model,
            cache_dir=str(cache),
            threads=2,
            providers=["CPUExecutionProvider"],
            cuda=False,
        )
        # A real inference catches incomplete downloads before enabling semantic mode.
        dimension = len(next(iter(embedding.embed(["local model readiness check"]))))
        model_dir = Path(embedding.model._model_dir).resolve()
        if not model_dir.is_relative_to(cache.resolve()):
            raise ValueError("Downloaded model escaped its configured cache")
        files = model_fingerprints(cache, model_dir)
        if not any(path.endswith(".onnx") for path in files):
            raise ValueError("Provisioning did not produce an ONNX model")
        identity = digest(
            json.dumps(
                {"model": model, "provider": version("fastembed"), "files": files}, sort_keys=True
            ).encode()
        )
        receipt = {
            "model": model,
            "provider": "fastembed",
            "provider_version": version("fastembed"),
            "identity": identity,
            "model_dir": model_dir.relative_to(cache.resolve()).as_posix(),
            "files": files,
            "dimensions": dimension,
            "provisioned_at": utcnow(),
        }
        _receipt_path(cache, model).parent.mkdir(exist_ok=True)
        atomic_text(_receipt_path(cache, model), json.dumps(receipt, indent=2))
        _load_cached.cache_clear()
    return {
        "state": "ready",
        "model": model,
        "identity": identity,
        "dimensions": dimension,
        "cache": str(cache),
        "network": "Used only for this explicit provisioning; subsequent loading uses the pinned local path",
    }


class LocalProvider:
    def __init__(self, cache: Path, receipt: dict):
        TextEmbedding = _text_embedding()
        model_dir = confined(cache, receipt["model_dir"])
        for relative, expected in receipt["files"].items():
            path = model_artifact(cache, model_dir, relative)
            if not path.is_file() or _file_hash(path) != expected:
                raise ValueError(
                    "Local model files changed or are incomplete; run semantic install again"
                )
        if version("fastembed") != receipt["provider_version"]:
            raise ValueError(
                "FastEmbed version changed; run semantic install to validate this provider/model combination"
            )
        self.identity = receipt["identity"]
        self.model = TextEmbedding(
            model_name=receipt["model"],
            cache_dir=str(cache),
            specific_model_path=str(model_dir),
            local_files_only=True,
            threads=2,
            providers=["CPUExecutionProvider"],
            cuda=False,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self.model.embed(texts, batch_size=32)]

    def embed_query(self, text: str) -> list[float]:
        return next(iter(self.model.query_embed(text))).tolist()


@lru_cache(maxsize=2)
def _load_cached(cache: str, receipt_json: str) -> LocalProvider:
    return LocalProvider(Path(cache), json.loads(receipt_json))


def load_provider(state: Path, model: str, configured_cache: str = "") -> LocalProvider:
    cache = cache_directory(state, configured_cache)
    path = _receipt_path(cache, model)
    if not path.is_file():
        raise ValueError(
            "Local model is not provisioned. Install the semantic extra and run semantic install."
        )
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if receipt["model"] != model or receipt["provider"] != "fastembed":
            raise ValueError("Semantic model receipt mismatch; run semantic install")
        return _load_cached(str(cache), json.dumps(receipt, sort_keys=True))
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid model receipt; run semantic install") from exc
