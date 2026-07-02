#!/usr/bin/env python3
"""Validate Crowdin wiring and Android resource translatability."""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CROWDIN_YML = REPO_ROOT / "crowdin.yml"

EXPECTED_SOURCES = {
    "app/src/main/res/values/strings.xml",
    "app/src/main/res/values/home_setup.xml",
    "app/src/main/res/values/dashboard_setup.xml",
    "app/src/main/res/values/blueprint_setup.xml",
    "app/src/main/res/values/about_setup.xml",
}

MUST_TRANSLATE = {
    "quick_apply_custom_text",
    "home_list_titles",
    "home_list_descriptions",
    "request_title",
    "credits_descriptions",
}

MUST_NOT_TRANSLATE = {
    "app_name",
    "toolbar_logo",
    "privacy_policy_link",
    "terms_conditions_link",
    "donation_items",
    "icons_placeholder",
    "static_icons_preview_picture",
    "email",
    "request_manager_backend_api_key",
    "request_manager_base_url",
    "home_list_icons",
    "home_list_links",
    "credits_photos",
    "credits_titles",
    "credits_links",
    "json_url",
    "wallpapers_json_urls",
}

MACHINE_VALUE_PATTERNS = (
    re.compile(r"^https?://", re.IGNORECASE),
    re.compile(r"^mailto:", re.IGNORECASE),
    re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
    re.compile(r"^ic_[a-z0-9_]+$"),
)


def _display(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _tag_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _translatable(element: ET.Element) -> bool:
    value = element.attrib.get("translatable", "true").strip().lower()
    return value != "false"


def _resource_values(element: ET.Element) -> list[str]:
    tag = _tag_name(element)
    if tag == "string":
        return [(element.text or "").strip()]
    if tag == "string-array":
        return [(item.text or "").strip() for item in element if _tag_name(item) == "item"]
    return []


def _looks_machine_value(value: str) -> bool:
    if value == "":
        return True
    return any(pattern.search(value) for pattern in MACHINE_VALUE_PATTERNS)


def _validate_xml(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return [f"{_display(path)}: invalid XML: {exc}"]

    for element in root:
        tag = _tag_name(element)
        if tag not in {"string", "string-array"}:
            continue
        name = element.attrib.get("name", "")
        if not name:
            errors.append(f"{_display(path)}: {tag} missing name")
            continue

        translatable = _translatable(element)
        values = _resource_values(element)

        if name in MUST_TRANSLATE and not translatable:
            errors.append(f"{_display(path)}: {name} must remain translatable")
        if name in MUST_NOT_TRANSLATE and translatable:
            errors.append(f"{_display(path)}: {name} must set translatable=\"false\"")
        if translatable and any(_looks_machine_value(value) for value in values):
            errors.append(f"{_display(path)}: {name} exposes blank or machine value(s) to translators")

    return errors


def _validate_crowdin_config() -> list[str]:
    errors: list[str] = []
    if not CROWDIN_YML.exists():
        return ["crowdin.yml is missing"]

    content = CROWDIN_YML.read_text(encoding="utf-8")
    if re.search(r"(?m)^\s*(project_id|api_token)\s*:", content):
        errors.append("crowdin.yml must use environment variables, not committed credentials")
    if "project_id_env: CROWDIN_PROJECT_ID" not in content:
        errors.append("crowdin.yml must read CROWDIN_PROJECT_ID")
    if "api_token_env: CROWDIN_PERSONAL_TOKEN" not in content:
        errors.append("crowdin.yml must read CROWDIN_PERSONAL_TOKEN")

    sources = {
        source.replace("\\", "/").lstrip("/")
        for source in re.findall(r"(?m)^\s*-\s*source:\s*\"?([^\"\n]+)\"?", content)
    }
    missing = sorted(EXPECTED_SOURCES - sources)
    extra = sorted(sources - EXPECTED_SOURCES)
    for source in missing:
        errors.append(f"crowdin.yml is missing source {source}")
    for source in extra:
        errors.append(f"crowdin.yml has unexpected source {source}")

    translation_lines = re.findall(r"(?m)^\s*translation:\s*\"?([^\"\n]+)\"?", content)
    if len(translation_lines) != len(EXPECTED_SOURCES):
        errors.append("crowdin.yml must define one translation path per source file")
    for translation in translation_lines:
        normalized = translation.replace("\\", "/")
        if "%android_code%" not in normalized:
            errors.append(f"crowdin.yml translation path lacks %android_code%: {translation}")
        if "%original_file_name%" not in normalized:
            errors.append(f"crowdin.yml translation path lacks %original_file_name%: {translation}")

    return errors


def main() -> int:
    errors = _validate_crowdin_config()
    for source in sorted(EXPECTED_SOURCES):
        errors.extend(_validate_xml(REPO_ROOT / source))

    if errors:
        print("validate_localization.py: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"validate_localization.py: OK ({len(EXPECTED_SOURCES)} Crowdin source files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
