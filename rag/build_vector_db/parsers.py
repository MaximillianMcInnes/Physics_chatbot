import re
from pathlib import Path
from typing import Dict, Tuple, Optional


TEXTBOOK_HEADER_RE = re.compile(
    r"^\[TEXTBOOK:\s*(?P<book>.*?)\s*\|\s*CHAPTER:\s*(?P<chapter>.*?)\s*\|\s*SECTION:\s*(?P<section>.*?)\s*\|\s*PRINTED_PAGES:\s*(?P<pages>.*?)\]\s*$",
    re.MULTILINE,
)

SME_LINK_RE = re.compile(r"^LINK:\s*(?P<link>https?://\S+)\s*$", re.MULTILINE)
SME_HEADING_RE = re.compile(r"^HEADING:\s*(?P<heading>.*?)\s*$", re.MULTILINE)

SPEC_LINE_RE = re.compile(r"^\[(?P<label>SPEC|TOPIC|SECTION|SUBSECTION):\s*(?P<value>.*?)\]\s*$", re.MULTILINE)


def clean_body(text: str) -> str:
    text = text.replace("\ufeff", "").strip()

    # Remove SaveMyExams long separator lines
    text = re.sub(r"^={10,}\s*$", "", text, flags=re.MULTILINE)

    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_textbook_file(text: str, path: Path) -> Tuple[str, Dict]:
    match = TEXTBOOK_HEADER_RE.search(text)
    metadata = {
        "source_type": "textbook",
        "file_name": path.name,
        "relative_path": str(path),
        "book": None,
        "chapter": None,
        "section": None,
        "printed_pages": None,
        "source_label": None,
        "url": None,
    }

    if match:
        metadata["book"] = match.group("book").strip()
        metadata["chapter"] = match.group("chapter").strip()
        metadata["section"] = match.group("section").strip()
        metadata["printed_pages"] = match.group("pages").strip()

        header_line = match.group(0)
        body = text.replace(header_line, "", 1).strip()
    else:
        body = text.strip()

    metadata["source_label"] = (
        f'Textbook | {metadata["chapter"] or "Unknown chapter"} | '
        f'{metadata["section"] or "Unknown section"} | '
        f'pp. {metadata["printed_pages"] or "?"}'
    )

    return clean_body(body), metadata


def parse_savemyexams_file(text: str, path: Path) -> Tuple[str, Dict]:
    link_match = SME_LINK_RE.search(text)
    heading_match = SME_HEADING_RE.search(text)

    metadata = {
        "source_type": "savemyexams",
        "file_name": path.name,
        "relative_path": str(path),
        "heading": heading_match.group("heading").strip() if heading_match else None,
        "url": link_match.group("link").strip() if link_match else None,
        "source_label": None,
        "book": None,
        "chapter": None,
        "section": None,
        "printed_pages": None,
    }

    body = text
    if link_match:
        body = body.replace(link_match.group(0), "", 1)
    if heading_match:
        body = body.replace(heading_match.group(0), "", 1)

    metadata["source_label"] = (
        f'Save My Exams | {metadata["heading"] or path.stem}'
    )

    return clean_body(body), metadata


def parse_spec_file(text: str, path: Path) -> Tuple[str, Dict]:
    lines = text.splitlines()

    metadata = {
        "source_type": "spec",
        "file_name": path.name,
        "relative_path": str(path),
        "spec": None,
        "topic": None,
        "section": None,
        "subsection": None,
        "url": None,
        "printed_pages": None,
        "book": None,
        "chapter": None,
        "source_label": None,
    }

    body_lines = []

    for line in lines:
        m = SPEC_LINE_RE.match(line.strip())
        if m:
            label = m.group("label").upper()
            value = m.group("value").strip()
            if label == "SPEC":
                metadata["spec"] = value
            elif label == "TOPIC":
                metadata["topic"] = value
            elif label == "SECTION":
                metadata["section"] = value
            elif label == "SUBSECTION":
                metadata["subsection"] = value
        else:
            body_lines.append(line)

    metadata["source_label"] = (
        f'Spec | {metadata["topic"] or "Unknown topic"}'
        + (f' | {metadata["section"]}' if metadata["section"] else "")
        + (f' | {metadata["subsection"]}' if metadata["subsection"] else "")
    )

    return clean_body("\n".join(body_lines)), metadata


def parse_file(path: Path, source_type: str) -> Tuple[str, Dict]:
    text = path.read_text(encoding="utf-8")

    if source_type == "textbook":
        return parse_textbook_file(text, path)
    if source_type == "savemyexams":
        return parse_savemyexams_file(text, path)
    if source_type == "spec":
        return parse_spec_file(text, path)

    raise ValueError(f"Unknown source_type: {source_type}")