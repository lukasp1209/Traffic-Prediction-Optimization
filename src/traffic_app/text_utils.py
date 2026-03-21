from __future__ import annotations

import re
from typing import List


def canonicalize_text(value: str) -> str:
    normalized = (
        str(value)
        .strip()
        .lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
        .replace("Ã¤", "ae")
        .replace("Ã¶", "oe")
        .replace("Ã¼", "ue")
        .replace("ÃŸ", "ss")
        .replace("ÃƒÂ¤", "ae")
        .replace("ÃƒÂ¶", "oe")
        .replace("ÃƒÂ¼", "ue")
        .replace("ÃƒÅ¸", "ss")
    )
    return " ".join(normalized.split())


def expand_osm_name_variants(name: str) -> List[str]:
    base = str(name).strip()
    if not base:
        return []

    variants = {base}
    variants.add(base.replace("ae", "ä").replace("oe", "ö").replace("ue", "ü"))
    variants.add(base.replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue"))
    variants.add(base.replace("ss", "ß"))
    variants.add(base.replace("Strasse", "Straße"))
    variants.add(base.replace("straße", "strasse"))
    variants.add(base.replace("Straße", "Strasse"))
    variants.add(base.replace("ae", "Ã¤").replace("oe", "Ã¶").replace("ue", "Ã¼"))
    variants.add(base.replace("Ã„", "Ae").replace("Ã–", "Oe").replace("Ãœ", "Ue"))
    variants.add(base.replace("ss", "ÃŸ"))
    variants.add(base.replace("Strasse", "StraÃŸe"))
    variants.add(base.replace("straÃŸe", "strasse"))
    variants.add(base.replace("StraÃŸe", "Strasse"))
    return [variant.strip() for variant in variants if variant.strip()]


def build_overpass_name_regex(name: str) -> str:
    variants = expand_osm_name_variants(name)
    escaped = [re.escape(variant) for variant in variants]
    return "|".join(sorted(set(escaped)))
