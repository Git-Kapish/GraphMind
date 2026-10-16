"""Entity name normalizer and string tokenization (PRD §8, Milestone M3)."""

import re

# Legal and corporate suffix regex pattern (PRD §8 rule 1)
LEGAL_SUFFIXES = [
    r"inc\.?",
    r"incorporated",
    r"corp\.?",
    r"corporation",
    r"llc",
    r"l\.l\.c\.?",
    r"ltd\.?",
    r"limited",
    r"co\.?",
    r"company",
    r"holdings?",
    r"group",
    r"plc",
    r"s\.a\.?",
    r"b\.v\.?",
    r"gmbh",
    r"opco",
    r"s\.r\.l\.?",
    r"pte\.?",
    r"sdn\.?\s*bhd\.?",
]

LEGAL_SUFFIX_PATTERN = re.compile(
    r"\b(" + "|".join(LEGAL_SUFFIXES) + r")\b",
    re.IGNORECASE,
)

# Known canonical enterprise mappings (PRD §8 rule 2)
KNOWN_ENTERPRISE_ALIASES: dict[str, str] = {
    "tsmc": "Taiwan Semiconductor Manufacturing Company",
    "taiwan semiconductor manufacturing company": "Taiwan Semiconductor Manufacturing Company",
    "taiwan semiconductor manufacturing company limited": "Taiwan Semiconductor Manufacturing Company",
    "taiwan semiconductor manufacturing co., ltd.": "Taiwan Semiconductor Manufacturing Company",
    "taiwan semiconductor": "Taiwan Semiconductor Manufacturing Company",
    "nvidia": "NVIDIA Corporation",
    "nvidia corp": "NVIDIA Corporation",
    "nvidia corporation": "NVIDIA Corporation",
    "amd": "Advanced Micro Devices, Inc.",
    "advanced micro devices": "Advanced Micro Devices, Inc.",
    "advanced micro devices, inc.": "Advanced Micro Devices, Inc.",
    "intel": "Intel Corporation",
    "intel corp": "Intel Corporation",
    "intel corporation": "Intel Corporation",
    "micron": "Micron Technology, Inc.",
    "micron technology": "Micron Technology, Inc.",
    "micron technology, inc.": "Micron Technology, Inc.",
    "microsoft": "Microsoft Corporation",
    "microsoft corp": "Microsoft Corporation",
    "microsoft corporation": "Microsoft Corporation",
    "broadcom": "Broadcom Inc.",
    "broadcom inc": "Broadcom Inc.",
    "broadcom inc.": "Broadcom Inc.",
    "openai": "OpenAI",
    "openai opco": "OpenAI",
    "openai opco, llc": "OpenAI",
    "sanmina": "Sanmina Corporation",
    "sanmina corp": "Sanmina Corporation",
    "sanmina corporation": "Sanmina Corporation",
    "cisco": "Cisco Systems, Inc.",
    "cisco systems": "Cisco Systems, Inc.",
    "cisco systems, inc.": "Cisco Systems, Inc.",
    "ibm": "International Business Machines",
    "international business machines": "International Business Machines",
    "hpe": "Hewlett Packard Enterprise",
    "hewlett packard enterprise": "Hewlett Packard Enterprise",
    "aws": "Amazon Web Services",
    "amazon web services": "Amazon Web Services",
    "supermicro": "Super Micro Computer",
    "super micro computer": "Super Micro Computer",
    "asml": "ASML Holding N.V.",
    "asml holding n.v.": "ASML Holding N.V.",
}


def clean_whitespace(text: str) -> str:
    """Normalize internal and external whitespace."""
    return re.sub(r"\s+", " ", text).strip()


def strip_parentheticals(text: str) -> str:
    """Strip trailing parenthetical acronyms or suffixes e.g. 'NVIDIA (NVDA)' -> 'NVIDIA'."""
    return clean_whitespace(re.sub(r"\s*\([^)]*\)$", "", text))


def strip_legal_suffixes(text: str) -> str:
    """Remove standard corporate suffixes (Inc, LLC, Corp, Ltd, etc.) from company names."""
    # Run twice to catch chained suffixes like 'Holdings Ltd.'
    stripped = LEGAL_SUFFIX_PATTERN.sub("", text)
    stripped = LEGAL_SUFFIX_PATTERN.sub("", stripped)
    # Clean trailing punctuation resulting from suffix removal
    stripped = stripped.rstrip(" ,.-/\\")
    return clean_whitespace(stripped)


def normalize_company_name(raw_name: str) -> str:
    """Normalize company name to canonical form (PRD §8 rule 1)."""
    if not raw_name:
        return "Unknown"

    cleaned = clean_whitespace(raw_name)
    lowered = cleaned.lower()

    # 1. Direct alias check
    if lowered in KNOWN_ENTERPRISE_ALIASES:
        return KNOWN_ENTERPRISE_ALIASES[lowered]

    # 2. Check after stripping parentheticals
    no_paren = strip_parentheticals(cleaned)
    if no_paren.lower() in KNOWN_ENTERPRISE_ALIASES:
        return KNOWN_ENTERPRISE_ALIASES[no_paren.lower()]

    # 3. Strip legal suffixes
    stripped = strip_legal_suffixes(no_paren)
    if stripped.lower() in KNOWN_ENTERPRISE_ALIASES:
        return KNOWN_ENTERPRISE_ALIASES[stripped.lower()]

    return stripped if len(stripped) >= 2 else no_paren


def tokenize_name(name: str) -> set[str]:
    """Tokenize entity name into set of lowercased alphanumeric words."""
    words = re.findall(r"\b[a-zA-Z0-9]+\b", name.lower())
    return set(words)


def extract_char_ngrams(text: str, n: int = 3) -> set[str]:
    """Extract character n-grams from normalized string for subword similarity."""
    cleaned = re.sub(r"[^a-zA-Z0-9]", "", text.lower())
    if len(cleaned) < n:
        return {cleaned} if cleaned else set()
    return {cleaned[i : i + n] for i in range(len(cleaned) - n + 1)}
