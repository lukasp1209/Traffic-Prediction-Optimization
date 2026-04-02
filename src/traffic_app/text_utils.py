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
        .replace("ÃƒÆ’Ã‚Â¤", "ae")
        .replace("ÃƒÆ’Ã‚Â¶", "oe")
        .replace("ÃƒÆ’Ã‚Â¼", "ue")
        .replace("ÃƒÆ’Ã…Â¸", "ss")
    )
    return " ".join(normalized.split())


def expand_osm_name_variants(name: str) -> List[str]:
    base = str(name).strip()
    if not base:
        return []

    variants = {base}
    variants.add(base.replace("ae", "ä").replace("oe", "ö").replace("ue", "ü"))
    variants.add(base.replace("Ae", "Ä").replace("Oe", "Ö").replace("Ue", "Ü"))
    variants.add(base.replace("ss", "ß"))
    variants.add(base.replace("Strasse", "Straße"))
    variants.add(base.replace("straße", "strasse"))
    variants.add(base.replace("Straße", "Strasse"))
    return [variant.strip() for variant in variants if variant.strip()]


def build_overpass_name_regex(name: str) -> str:
    variants = expand_osm_name_variants(name)
    escaped = [re.escape(variant) for variant in variants]
    return "|".join(sorted(set(escaped)))
