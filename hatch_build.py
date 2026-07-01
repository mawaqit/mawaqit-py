"""Hatch build customisations.

Two project-local plugins, both loaded via Hatch's ``custom`` convention:

* :class:`EnvVersionMetadataHook` — resolves the (dynamic) package version from
  the ``VERSION`` environment variable (set to the release tag in CI, aligned to
  the newest supported API version), defaulting to ``0.0.0`` for local/editable
  installs.
* :class:`GenerateBuildHook` — regenerates ``mawaqit/_generated`` (pydantic
  models from the swagger specs) and ``mawaqit/_sync`` (unasync-derived sync
  client) before the artifact is assembled, so the gitignored generated code is
  always present in the built wheel/sdist.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.metadata.plugin.interface import MetadataHookInterface


class EnvVersionMetadataHook(MetadataHookInterface):
    PLUGIN_NAME = "custom"

    def update(self, metadata: dict[str, Any]) -> None:
        metadata["version"] = os.environ.get("VERSION", "0.0.0")


class GenerateBuildHook(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        subprocess.run(
            [sys.executable, "scripts/generate.py"],
            check=True,
            cwd=self.root,
        )
