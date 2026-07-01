#!/usr/bin/env python
"""Regenerate the gitignored code the library depends on.

Two outputs, both derived mechanically from the checked-in swagger specs so
they can never silently diverge from the real API:

* ``mawaqit/_generated/v{N}.py`` — pydantic v2 models, one module per API
  version, produced by ``datamodel-code-generator``.
* ``mawaqit/_sync/`` — the synchronous client, produced from the hand-written
  async source (``mawaqit/_async``) by ``unasync``.

Run directly (``python scripts/generate.py``) or via the Hatch build hook.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import unasync
import yaml

ROOT = Path(__file__).resolve().parent.parent
SWAGGER_DIR = ROOT / "swagger"
GENERATED_DIR = ROOT / "mawaqit" / "_generated"
ASYNC_DIR = ROOT / "mawaqit" / "_async"
SYNC_DIR = ROOT / "mawaqit" / "_sync"

# Token-level renames applied on top of unasync's defaults (which already strip
# async/await and rewrite the async dunders). Keys are whole NAME tokens.
SYNC_REPLACEMENTS = {
    "AsyncMawaqitClient": "MawaqitClient",
    "AsyncClient": "Client",  # httpx.AsyncClient -> httpx.Client
    "AsyncV2": "SyncV2",
    "AsyncV3": "SyncV3",
    "aclose": "close",
    "asyncio": "time",  # `from asyncio import sleep` -> `from time import sleep`
}

# swagger spec filename (stem) -> generated module name
VERSIONS = {"2.0": "v2", "3.0": "v3"}


def _to_openapi3(spec: dict[str, Any]) -> str:
    """Lift a Swagger 2.0 ``definitions`` block into a minimal OpenAPI 3 doc.

    datamodel-code-generator's OpenAPI parser reads models from
    ``components/schemas``; Swagger 2.0 keeps them under ``definitions`` with
    ``#/definitions/`` refs. We only need the schemas (not the paths) to emit
    models, so we wrap them and rewrite the ref prefix.
    """
    doc = {
        "openapi": "3.0.3",
        "info": spec.get("info", {"title": "MAWAQIT", "version": "0"}),
        "paths": {},
        "components": {"schemas": spec.get("definitions", {})},
    }
    return json.dumps(doc).replace("#/definitions/", "#/components/schemas/")


def generate_models() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    (GENERATED_DIR / "__init__.py").write_text(
        '"""Pydantic models generated from the swagger specs. Do not edit."""\n'
    )

    for stem, module in VERSIONS.items():
        spec = yaml.safe_load((SWAGGER_DIR / f"{stem}.yml").read_text())
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
            tmp.write(_to_openapi3(spec))
            tmp_path = tmp.name

        out = GENERATED_DIR / f"{module}.py"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "datamodel_code_generator",
                "--input",
                tmp_path,
                "--input-file-type",
                "openapi",
                "--output-model-type",
                "pydantic_v2.BaseModel",
                "--target-python-version",
                "3.10",
                "--use-standard-collections",
                "--use-union-operator",
                "--use-annotated",
                "--field-constraints",
                "--use-schema-description",
                "--formatters",
                "ruff-format",
                "--output",
                str(out),
            ],
            check=True,
            cwd=ROOT,
        )
        Path(tmp_path).unlink()
        print(f"generated {out.relative_to(ROOT)}")


def generate_sync() -> None:
    """Derive the sync client under ``mawaqit/_sync`` from ``mawaqit/_async``."""
    if SYNC_DIR.exists():
        shutil.rmtree(SYNC_DIR)
    SYNC_DIR.mkdir(parents=True)

    rule = unasync.Rule(
        fromdir=str(ASYNC_DIR) + os.sep,
        todir=str(SYNC_DIR) + os.sep,
        additional_replacements=SYNC_REPLACEMENTS,
    )
    sources = sorted(str(path) for path in ASYNC_DIR.glob("*.py"))
    unasync.unasync_files(sources, [rule])
    print(f"generated {SYNC_DIR.relative_to(ROOT)}/ from {len(sources)} async modules")


def main() -> None:
    generate_models()
    generate_sync()


if __name__ == "__main__":
    main()
