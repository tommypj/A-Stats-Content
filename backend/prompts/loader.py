"""
Prompt loader — reads versioned prompt templates and config from disk.

All prompt prose lives in /prompts/ files so adapters stay logic-only.
Templates use Python str.format() placeholders: {variable_name}.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent


class PromptLoader:
    """Loads and caches prompt templates and config files from the prompts directory."""

    def __init__(self) -> None:
        self._template_cache: dict[str, str] = {}
        self._config_cache: dict[str, dict] = {}
        self._manifest: dict | None = None

    def _get_manifest(self) -> dict:
        if self._manifest is None:
            manifest_path = _PROMPTS_DIR / "manifest.json"
            with open(manifest_path, encoding="utf-8") as f:
                self._manifest = json.load(f)
        return self._manifest

    def get_template(self, name: str) -> str:
        """Load a prompt template by name (e.g. 'article_generation').

        Returns the raw template string with {placeholder} variables.
        """
        if name in self._template_cache:
            return self._template_cache[name]

        manifest = self._get_manifest()
        entry = manifest["prompts"].get(name)
        if not entry:
            raise KeyError(f"Unknown prompt template: {name}")

        path = _PROMPTS_DIR / entry["path"]
        template = path.read_text(encoding="utf-8")
        self._template_cache[name] = template
        return template

    def format(self, name: str, **kwargs: Any) -> str:
        """Load a prompt template and format it with the given variables.

        Uses str.format_map with a defaultdict so missing keys produce
        empty strings instead of raising KeyError.
        """
        template = self.get_template(name)
        safe = _SafeDict(kwargs)
        return template.format_map(safe)

    def get_version(self, name: str) -> str:
        """Return the current version string for a prompt (e.g. '1.0')."""
        manifest = self._get_manifest()
        entry = manifest["prompts"].get(name)
        if not entry:
            raise KeyError(f"Unknown prompt template: {name}")
        return entry["version"]

    def get_config(self, name: str) -> dict:
        """Load a JSON config file by name (e.g. 'writing_styles').

        Returns the parsed dict.
        """
        if name in self._config_cache:
            return self._config_cache[name]

        manifest = self._get_manifest()
        rel_path = manifest["config"].get(name)
        if not rel_path:
            raise KeyError(f"Unknown config: {name}")

        path = _PROMPTS_DIR / rel_path
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self._config_cache[name] = data
        return data

    def clear_cache(self) -> None:
        """Clear all cached templates and configs (useful for hot-reload in dev)."""
        self._template_cache.clear()
        self._config_cache.clear()
        self._manifest = None


class _SafeDict(dict):
    """Dict subclass that returns '' for missing keys in str.format_map()."""

    def __missing__(self, key: str) -> str:
        return ""


# Module-level singleton
prompt_loader = PromptLoader()
