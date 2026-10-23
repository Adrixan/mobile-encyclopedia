"""Resource catalog and declarative metadata loader."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

import yaml

ALLOWED_SCHEMES = {"https"}
VALID_FORMATS = {"zim", "map", "epub", "tar", "zip", "kolibri"}
VALID_CATEGORIES = {"admin", "dev", "tutorials", "wiki", "survival", "maps", "qna", "fun", "tools"}
VALID_SOURCES = {"url", "kiwix", "github", "kolibri"}
VALID_KIWIX_FLAVOURS = {"", "maxi", "nopic", "mini"}
ARCHIVE_FORMATS = {"zip", "tar"}

_KIWIX_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._\-]*$")
_GITHUB_REPO_RE = re.compile(r"^[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+$")
_KOLIBRI_CHANNEL_RE = re.compile(r"^[0-9a-f]{32}$")


def get_default_catalog_file() -> Path:
    """Return path to packaged catalog.yaml."""
    return Path(__file__).parent / "data" / "catalog.yaml"


@dataclass
class ResourceItem:
    """A single offline resource item."""

    id: str
    name: str
    category: str
    language: str
    format: str
    size_mb: int
    upstream_url: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    source: str = "url"
    kiwix_name: str = ""
    kiwix_flavour: str = ""
    github_repo: str = ""
    asset_pattern: str = ""
    kolibri_channel: str = ""
    entrypoint: str = ""
    extract_subdir: str = ""
    serve_root: bool = False

    @property
    def is_archive(self) -> bool:
        """True if the download is a web app archive that is extracted into a folder."""
        return self.format in ARCHIVE_FORMATS

    def matches_query(self, query: str) -> bool:
        """Check if item matches search query."""
        q = query.lower()
        if q.startswith("lang:"):
            target_lang = q.split(":", 1)[1].strip()
            return self.language.lower() == target_lang
        if q.startswith("cat:"):
            target_cat = q.split(":", 1)[1].strip()
            return self.category.lower() == target_cat
        if q.startswith("tag:"):
            target_tag = q.split(":", 1)[1].strip()
            return any(target_tag in t.lower() for t in self.tags)

        # Keyword match
        return (
            q in self.id.lower()
            or q in self.name.lower()
            or q in self.description.lower()
            or any(q in t.lower() for t in self.tags)
        )


def _validate_relative_path(value: str, field_name: str, allow_query: bool = False) -> str:
    """Reject absolute paths, traversal and control characters in archive-relative paths."""
    path_part = value.split("?", 1)[0] if allow_query else value
    if (
        "\x00" in value
        or "\\" in value
        or path_part.startswith("/")
        or ".." in path_part.split("/")
        or (not allow_query and "?" in value)
    ):
        raise ValueError(f"Invalid {field_name}: {value}")
    return value


def _validate_source(data: Dict[str, Any], res_id: str, fmt: str) -> Dict[str, str]:
    """Validate typed upstream source fields and return them normalized."""
    source = str(data.get("source", "url")).lower()
    if source not in VALID_SOURCES:
        raise ValueError(f"Invalid source '{source}' in resource {res_id}")

    fields = {
        "source": source,
        "kiwix_name": str(data.get("kiwix_name", "")),
        "kiwix_flavour": str(data.get("kiwix_flavour", "")),
        "github_repo": str(data.get("github_repo", "")),
        "asset_pattern": str(data.get("asset_pattern", "")),
        "kolibri_channel": str(data.get("kolibri_channel", "")),
    }

    if source == "kiwix":
        if not _KIWIX_NAME_RE.match(fields["kiwix_name"]):
            raise ValueError(f"Missing or invalid kiwix_name in resource {res_id}")
        if fields["kiwix_flavour"] not in VALID_KIWIX_FLAVOURS:
            raise ValueError(f"Invalid kiwix flavour '{fields['kiwix_flavour']}' in resource {res_id}")
    elif source == "github":
        if not _GITHUB_REPO_RE.match(fields["github_repo"]):
            raise ValueError(f"Missing or invalid github_repo in resource {res_id}")
        try:
            re.compile(fields["asset_pattern"])
        except re.error as exc:
            raise ValueError(f"Invalid asset_pattern in resource {res_id}: {exc}") from exc
        if not fields["asset_pattern"]:
            raise ValueError(f"Missing asset_pattern in resource {res_id}")
    elif source == "kolibri":
        if not _KOLIBRI_CHANNEL_RE.match(fields["kolibri_channel"]):
            raise ValueError(f"Missing or invalid kolibri_channel in resource {res_id}")
        if fmt != "kolibri":
            raise ValueError(f"Kolibri source requires format 'kolibri' in resource {res_id}")
    if fmt == "kolibri" and source != "kolibri":
        raise ValueError(f"Format 'kolibri' requires source 'kolibri' in resource {res_id}")
    return fields


def validate_resource_item(data: Dict[str, Any]) -> ResourceItem:
    """Validate resource metadata and schema with strict security checks."""
    if not isinstance(data, dict):
        raise ValueError("Resource item must be a dictionary")

    required_fields = ["id", "name", "category", "language", "format", "size_mb", "upstream_url"]
    for f in required_fields:
        if f not in data:
            raise ValueError(f"Missing required catalog field: {f}")

    # Security check: URL must be HTTPS
    url = str(data["upstream_url"])
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES or not parsed.netloc:
        raise ValueError(f"Insecure or invalid URL protocol for {data.get('id')}: {url}")

    # Validate format and category
    fmt = str(data["format"]).lower()
    if fmt not in VALID_FORMATS:
        raise ValueError(f"Invalid format '{fmt}' in resource {data.get('id')}")

    cat = str(data["category"]).lower()
    if cat not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category '{cat}' in resource {data.get('id')}")

    # ID sanitization (alphanumeric + underscore/hyphen)
    res_id = str(data["id"])
    if not re.match(r"^[a-zA-Z0-9_\-]+$", res_id):
        raise ValueError(f"Invalid characters in resource ID: {res_id}")

    source_fields = _validate_source(data, res_id, fmt)
    entrypoint = _validate_relative_path(str(data.get("entrypoint", "")), "entrypoint", allow_query=True)
    extract_subdir = _validate_relative_path(str(data.get("extract_subdir", "")).rstrip("/"), "extract_subdir")
    serve_root = data.get("serve_root", False)
    if not isinstance(serve_root, bool):
        raise ValueError(f"serve_root must be true or false in resource {res_id}")

    return ResourceItem(
        id=res_id,
        name=str(data["name"]),
        category=cat,
        language=str(data["language"]).lower(),
        format=fmt,
        size_mb=int(data["size_mb"]),
        upstream_url=url,
        description=str(data.get("description", "")),
        tags=[str(t) for t in data.get("tags", [])],
        entrypoint=entrypoint,
        extract_subdir=extract_subdir,
        serve_root=serve_root,
        **source_fields,
    )


class ResourceCatalog:
    """Catalog manager for offline resources."""

    def __init__(self, items: List[ResourceItem]) -> None:
        self.items = items
        self._by_id = {item.id: item for item in items}

    def get_by_id(self, item_id: str) -> Optional[ResourceItem]:
        """Retrieve resource item by unique ID."""
        return self._by_id.get(item_id)

    def get_categories(self) -> List[str]:
        """Return unique list of sorted categories."""
        return sorted(list({item.category for item in self.items}))

    def get_languages(self) -> List[str]:
        """Return unique list of sorted languages."""
        return sorted(list({item.language for item in self.items}))

    def filter(
        self,
        category: Optional[str] = None,
        language: Optional[str] = None,
        format_type: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[ResourceItem]:
        """Filter resources by multiple criteria."""
        results = self.items
        if category:
            results = [i for i in results if i.category.lower() == category.lower()]
        if language:
            results = [i for i in results if i.language.lower() == language.lower()]
        if format_type:
            results = [i for i in results if i.format.lower() == format_type.lower()]
        if tag:
            results = [i for i in results if any(tag.lower() == t.lower() for t in i.tags)]
        return results

    def search(self, query: str) -> List[ResourceItem]:
        """Search items by search query or tag/lang prefix."""
        if not query.strip():
            return list(self.items)
        return [i for i in self.items if i.matches_query(query)]

    def calculate_total_size_mb(self, item_ids: List[str] | Set[str]) -> int:
        """Calculate total size in megabytes for selected resource IDs."""
        total = 0
        for item_id in item_ids:
            item = self._by_id.get(item_id)
            if item:
                total += item.size_mb
        return total


def load_catalog(catalog_path: Optional[Path] = None) -> ResourceCatalog:
    """Load and validate resource catalog from YAML file."""
    path = catalog_path or get_default_catalog_file()
    if not path.is_file():
        raise FileNotFoundError(f"Catalog file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    raw_resources = data.get("resources", [])
    if not isinstance(raw_resources, list):
        raise ValueError("Invalid catalog format: 'resources' must be a list")

    validated_items: List[ResourceItem] = []
    for raw in raw_resources:
        item = validate_resource_item(raw)
        validated_items.append(item)

    return ResourceCatalog(validated_items)
