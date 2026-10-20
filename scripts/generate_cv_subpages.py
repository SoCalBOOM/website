#!/usr/bin/env python3
"""
Generate Quarto include fragments for CV sections from a BibTeX file.

Usage:
  python3 scripts/generate_cv_subpages.py

This script reads:
  - jlanders_CV/CV_ref.bib

And writes:
  - subpages/generated/bibliography/posters.qmd               (type: inproceedings)
  - subpages/generated/bibliography/articles.qmd              (type: article)
  - subpages/generated/bibliography/educational_materials.qmd (type: edumat)
  - subpages/generated/bibliography/seminars.qmd              (type: talk)
  - subpages/generated/bibliography/conference_talks.qmd      (type: unpublished)
  - subpages/generated/bibliography/software.qmd              (type: software)
  - subpages/generated/...               (site-specific routed fragments)

It is run by _quarto.yml before each site render, so editing the .bib file
updates every generated fragment.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List


ROOT = Path(__file__).resolve().parent.parent
BIB_PATH = ROOT / "jlanders_CV" / "CV_ref.bib"
OUT_DIR = ROOT / "subpages"
BIB_OUT_DIR = OUT_DIR / "generated" / "bibliography"

CATEGORY_TO_TYPE = {
    "posters.qmd": "inproceedings",
    "articles.qmd": "article",
    "educational_materials.qmd": "edumat",
    "seminars.qmd": "talk",
    "conference_talks.qmd": "unpublished",
    "software.qmd": "software",
}

# The route names are deliberately separate from the CV entry type. An item
# may, for example, be an article in the CV while also belonging on the
# nonlinear-causality page and in the paleoclimate overview.
OVERVIEW_SECTIONS = ("paleoclimate", "open-edu", "software", "etc")
SITE_PAGE_SECTIONS = {
    "nonlinear-causality": {
        "references": ("article",),
        "talks": ("unpublished", "talk"),
        "posters": ("inproceedings",),
    },
    "open-science": {
        "posters": ("inproceedings",),
        "educational-materials": ("edumat",),
    },
}


@dataclass
class BibEntry:
    entry_type: str
    key: str
    fields: Dict[str, str]


def strip_outer_wrappers(value: str) -> str:
    text = value.strip()
    while len(text) >= 2 and (
        (text.startswith("{") and text.endswith("}"))
        or (text.startswith('"') and text.endswith('"'))
    ):
        text = text[1:-1].strip()
    return text


def strip_inner_braces(text: str) -> str:
    """Remove BibTeX capitalization-protection braces from inside a
    field, e.g. 'the {GNAIW} variability' -> 'the GNAIW variability'.

    strip_outer_wrappers only peels a brace pair that wraps the *whole*
    field; this handles the much more common case of a protected word
    or phrase somewhere in the middle of it. Since these braces are
    purely a BibTeX capitalization hint with no display meaning, it's
    always safe to just drop the characters.
    """
    return text.replace("{", "").replace("}", "")


def clean_latex_math(text: str) -> str:
    """Flatten simple inline LaTeX math down to plain text, e.g.
    'CO${_2}$' -> 'CO2'. This only handles the subscript/superscript
    case actually seen in this CV's .bib (a bare $...$ span whose only
    content is a _{...} or ^{...} group) — it's a light touch-up, not a
    general LaTeX-to-text converter.
    """
    text = re.sub(r"\$([^$]*)\$", r"\1", text)
    text = text.replace("_", "").replace("^", "")
    return text


def clean_prose(value: str) -> str:
    """The standard cleanup pass for a free-text field (title, venue,
    address, note): unwrap outer braces/quotes, drop any inner
    protection braces, flatten simple LaTeX math, then collapse
    whitespace.
    """
    text = strip_outer_wrappers(value)
    text = strip_inner_braces(text)
    text = clean_latex_math(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_text(value: str) -> str:
    text = strip_outer_wrappers(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text


_INITIAL_TOKEN_RE = re.compile(r"[A-Za-z][a-zA-Z\-]*\.?")


def to_initials(given: str) -> str:
    """Reduce a given-name field to glued initials: 'Julien' -> 'J.',
    'Alexander K.' -> 'A.K.', and 'J.P.' (already initials) -> 'J.P.'
    unchanged. Each whitespace/period-delimited token becomes one
    initial; tokens that are already a bare initial (a single letter
    plus a trailing period) pass through as-is.
    """
    tokens = _INITIAL_TOKEN_RE.findall(given)
    initials = []
    for token in tokens:
        if len(token) <= 2 and token.endswith("."):
            initials.append(token)
        else:
            initials.append(token[0].upper() + ".")
    return "".join(initials)


def format_author(segment: str) -> str:
    """Normalize one author name to 'Last, Initials' form.

    Handles both BibTeX author orderings found in this CV's .bib:
    already 'Last, Given' (just clean it up and reduce the given part
    to initials), and 'Given Last' with no comma (assume the final
    whitespace-separated token is the surname — true for every name in
    this file, though it isn't a universal rule for names with
    multi-word surnames or particles like 'van der').
    """
    text = strip_inner_braces(strip_outer_wrappers(segment)).strip()
    if not text:
        return ""
    if "," in text:
        last, _, given = text.partition(",")
        last = last.strip()
        initials = to_initials(given)
        return f"{last}, {initials}" if initials else last
    tokens = text.split()
    if len(tokens) < 2:
        return text
    *given_tokens, surname = tokens
    initials = to_initials(" ".join(given_tokens))
    return f"{surname}, {initials}" if initials else surname


def format_author_list(raw: str) -> str:
    """Split a BibTeX 'and'-joined author field and render it as
    'Last, F.M., Last, F.M. & Last, F.M.' — comma-separated, with '&'
    (not a comma) before the final name.
    """
    text = strip_outer_wrappers(raw)
    # A stray comma sometimes precedes "and" in this CV's .bib (e.g.
    # "T.P. Guilderson, and K.A. Allen, and ..."); fold it into the
    # separator before splitting so it doesn't linger on the segment.
    text = re.sub(r",\s+and\s+", " and ", text)
    segments = [s for s in re.split(r"\s+and\s+", text) if s.strip()]
    names = [format_author(s) for s in segments]
    names = [n for n in names if n]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " & " + names[-1]


_URL_MACRO_RE = re.compile(r"\\url\{([^{}]*)\}")
_TRAILING_NOTE_RE = re.compile(r"\{(\([^{}]*\))\}\s*$")


def extract_url_macro(text: str) -> tuple[str, str | None]:
    """Pull a raw '\\url{...}' macro (sometimes embedded directly in a
    title instead of using a dedicated url= field) out of a field,
    returning the field with it removed and the URL found, if any.
    """
    match = _URL_MACRO_RE.search(text)
    if not match:
        return text, None
    remainder = text[: match.start()] + text[match.end() :]
    remainder = re.sub(r"[,\s]+$", "", remainder).strip()
    return remainder, match.group(1)


def extract_trailing_note(raw_title: str) -> tuple[str, str | None]:
    """Pull a brace-protected trailing parenthetical — an abstract or
    session ID like '{(PP13B-1430)}' — off the end of a raw title.

    Requiring the BibTeX author to have already marked it as its own
    protected group (rather than pattern-matching on what an ID
    'looks like') is what makes this safe to apply generally: it only
    fires when the source data itself signals "this trailing bit is a
    separate unit," so it can't misfire on an ordinary parenthetical
    that happens to end a title.
    """
    text = strip_outer_wrappers(raw_title)
    match = _TRAILING_NOTE_RE.search(text)
    if not match:
        return text, None
    remainder = text[: match.start()].rstrip()
    return remainder, match.group(1)


def parse_year(value: str) -> int:
    text = normalize_text(value)
    m = re.search(r"\d{4}", text)
    return int(m.group(0)) if m else -1


def strip_bib_comments(text: str) -> str:
    """Remove '%' comments to end-of-line (unless escaped as '\\%')."""
    out: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "%" and (i == 0 or text[i - 1] != "\\"):
            while i < n and text[i] not in "\r\n":
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def parse_bibtex_entries(text: str) -> List[BibEntry]:
    text = strip_bib_comments(text)
    entries: List[BibEntry] = []
    i = 0
    n = len(text)

    while i < n:
        at = text.find("@", i)
        if at == -1:
            break

        j = at + 1
        while j < n and (text[j].isalnum() or text[j] in "_-"):
            j += 1
        if j == at + 1:
            i = at + 1
            continue

        entry_type = text[at + 1 : j].strip().lower()

        while j < n and text[j].isspace():
            j += 1
        if j >= n or text[j] != "{":
            i = at + 1
            continue

        depth = 0
        k = j
        while k < n:
            ch = text[k]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            k += 1

        # Tolerant behavior: malformed trailing content is skipped.
        if k >= n:
            break

        inner = text[j + 1 : k].strip()
        parsed = parse_entry_inner(entry_type, inner)
        if parsed is not None:
            entries.append(parsed)

        i = k + 1

    return entries


def parse_entry_inner(entry_type: str, inner: str) -> BibEntry | None:
    if not inner:
        return None

    comma_idx = find_top_level_comma(inner)
    if comma_idx == -1:
        return None

    key = inner[:comma_idx].strip()
    if not key:
        return None

    fields_blob = inner[comma_idx + 1 :]
    fields = parse_fields(fields_blob)
    return BibEntry(entry_type=entry_type, key=key, fields=fields)


def find_top_level_comma(text: str) -> int:
    depth = 0
    in_quotes = False
    escape = False
    for idx, ch in enumerate(text):
        if in_quotes:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_quotes = False
            continue

        if ch == '"':
            in_quotes = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            return idx
    return -1


def parse_fields(blob: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    i = 0
    n = len(blob)

    while i < n:
        while i < n and (blob[i].isspace() or blob[i] == ","):
            i += 1
        if i >= n:
            break

        name_start = i
        while i < n and (blob[i].isalnum() or blob[i] in "_-"):
            i += 1
        if i == name_start:
            i += 1
            continue

        field_name = blob[name_start:i].strip().lower()
        while i < n and blob[i].isspace():
            i += 1
        if i >= n or blob[i] != "=":
            i += 1
            continue
        i += 1
        while i < n and blob[i].isspace():
            i += 1
        if i >= n:
            break

        value, i = read_value(blob, i)
        fields[field_name] = value.strip()

    return fields


def read_value(text: str, i: int) -> tuple[str, int]:
    n = len(text)
    if i >= n:
        return "", i

    if text[i] == "{":
        depth = 0
        start = i
        while i < n:
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    i += 1
                    return text[start:i], i
            i += 1
        return text[start:], n

    if text[i] == '"':
        start = i
        i += 1
        escape = False
        while i < n:
            ch = text[i]
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                i += 1
                break
            i += 1
        return text[start:i], i

    start = i
    while i < n and text[i] not in ",\n\r":
        i += 1
    return text[start:i], i


def sanitize_url(url: str) -> str:
    text = normalize_text(url)
    text = re.sub(r"^\\url\{", "", text)
    text = re.sub(r"\}$", "", text)
    return text


def doi_url(doi: str) -> str:
    """Return a clickable DOI resolver URL for either DOI input form."""
    text = normalize_text(doi)
    if not text:
        return ""
    if re.match(r"https?://", text, flags=re.IGNORECASE):
        return text
    return "https://doi.org/" + text.removeprefix("doi:").strip()


# Recurring venue names whose BibTeX booktitle drops the year (AGU's
# own abstract-submission system exports every entry with the generic
# booktitle "AGU Fall Meeting Abstracts", regardless of which year's
# meeting it was) — fold the entry's own year in and drop "Abstracts".
_YEARLESS_VENUES = {
    "AGU Fall Meeting Abstracts": "AGU Fall Meeting {year}",
}


def format_venue(raw: str, year: str) -> str:
    venue = clean_prose(raw)
    template = _YEARLESS_VENUES.get(venue)
    if template and year:
        return template.format(year=year)
    return venue


def format_entry(entry: BibEntry) -> str:
    f = entry.fields
    year = normalize_text(f.get("year", ""))
    author = format_author_list(f.get("author", ""))

    raw_title, trailing_note = extract_trailing_note(f.get("title", ""))
    raw_title, embedded_url = extract_url_macro(raw_title)
    title = clean_prose(raw_title)

    venue = format_venue(f.get("journal", ""), year) or format_venue(
        f.get("booktitle", ""), year
    )
    address = clean_prose(f.get("address", ""))
    note = clean_prose(f.get("note", ""))
    # Prefer an explicitly supplied URL. If none is present, a DOI resolver is
    # the most stable public link to a paper and avoids duplicate URL fields.
    url = sanitize_url(f.get("url", "")) or embedded_url or doi_url(f.get("doi", ""))

    parts: List[str] = []
    if year:
        parts.append(f"**{year}**")
    if author:
        parts.append(author)
    if title:
        title_part = f'"{title}"'
        if trailing_note:
            title_part += f" {trailing_note}"
        parts.append(title_part)
    if venue:
        parts.append(venue)
    if address:
        parts.append(address)
    if note:
        parts.append(note)
    if url:
        parts.append(f"[link]({url})")

    if not parts:
        parts.append(entry.key)

    return "- " + ". ".join(parts) + "."


def sort_entries(entries: List[BibEntry]) -> List[BibEntry]:
    def sort_key(entry: BibEntry) -> tuple[int, str, str]:
        year = parse_year(entry.fields.get("year", ""))
        title = normalize_text(entry.fields.get("title", "")).lower()
        return (year, title, entry.key.lower())

    return sorted(entries, key=sort_key, reverse=True)


def split_route_values(value: str) -> set[str]:
    """Return the comma-separated routing values from a custom BibTeX field."""
    return {
        item.strip().lower()
        for item in clean_prose(value).split(",")
        if item.strip()
    }


def build_output(entries: List[BibEntry]) -> str:
    if not entries:
        return "<!-- No entries found for this category. -->\n"
    lines = [format_entry(e) for e in entries]
    return "\n".join(lines) + "\n"


def main() -> None:
    if not BIB_PATH.exists():
        raise SystemExit(f"Missing BibTeX file: {BIB_PATH}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BIB_OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw = BIB_PATH.read_text(encoding="utf-8")
    all_entries = parse_bibtex_entries(raw)

    for filename, bib_type in CATEGORY_TO_TYPE.items():
        filtered = [e for e in all_entries if e.entry_type == bib_type]
        filtered = sort_entries(filtered)
        output_text = build_output(filtered)
        (BIB_OUT_DIR / filename).write_text(output_text, encoding="utf-8")

    generated_dir = OUT_DIR / "generated"
    for overview_section in OVERVIEW_SECTIONS:
        entries = [
            entry
            for entry in all_entries
            if overview_section in split_route_values(
                entry.fields.get("site_overview", "")
            )
        ]
        path = generated_dir / "overview" / f"{overview_section}.qmd"
        path.parent.mkdir(parents=True, exist_ok=True)
        output_text = build_output(sort_entries(entries))
        path.write_text(output_text, encoding="utf-8")

    for page, sections in SITE_PAGE_SECTIONS.items():
        for section, entry_types in sections.items():
            entries = [
                entry
                for entry in all_entries
                if entry.entry_type in entry_types
                and page in split_route_values(entry.fields.get("site_pages", ""))
            ]
            path = generated_dir / page / f"{section}.qmd"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(build_output(sort_entries(entries)), encoding="utf-8")

    print(f"Parsed {len(all_entries)} entries from {BIB_PATH}")
    for filename, bib_type in CATEGORY_TO_TYPE.items():
        count = sum(1 for e in all_entries if e.entry_type == bib_type)
        print(f"{filename}: {count} ({bib_type})")


if __name__ == "__main__":
    main()
