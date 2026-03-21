import os
import re
import fitz  # PyMuPDF

# =========================================================
# CONFIG
# =========================================================
PDF_PATH = "textbook.pdf"
OUTPUT_DIR = "textbook_sections"
TEXTBOOK_NAME = "My Revision Notes AQA A-level Physics"

# page numbers below are the printed textbook page numbers you gave
# if PDF page numbering is different, adjust PDF_PAGE_OFFSET
PDF_PAGE_OFFSET = 0
# example:
# if printed page 5 is actually PDF page 9, then use:
# PDF_PAGE_OFFSET = 4

SECTIONS = [
    ("1", "Measurements and their errors", 7, [
        ("1.1", "Use of SI units and their prefixes", 7),
        ("1.2", "Limitation of physical measurements", 9),
        ("1.3", "Estimation of physical quantities", 11),
    ]),
    ("2", "Particles and radiation", 13, [
        ("2.1", "Constituents of the atom", 13),
        ("2.2", "Stable and unstable nuclei", 15),
        ("2.3", "Particles, antiparticles and photons", 16),
        ("2.4", "Particle interactions", 19),
        ("2.5", "Classification of particles", 21),
        ("2.6", "Quarks and antiquarks", 23),
        ("2.7", "Applications of conservation laws", 24),
        ("2.8", "The photoelectric effect", 25),
        ("2.9", "Collisions of electrons with atoms", 27),
        ("2.10", "Energy levels and photon emission", 29),
        ("2.11", "Wave–particle duality", 30),
    ]),
    ("3", "Waves", 34, [
        ("3.1", "Progressive waves", 34),
        ("3.2", "Longitudinal and transverse waves", 35),
        ("3.3", "Principle of superposition of waves and formation of stationary waves", 37),
        ("3.4", "Interference", 40),
        ("3.5", "Diffraction", 43),
        ("3.6", "Refraction at a plane surface", 47),
    ]),
    ("4", "Mechanics and materials", 54, [
        ("4.1", "Scalars and vectors", 54),
        ("4.2", "Moments", 57),
        ("4.3", "Motion along a straight line", 62),
        ("4.4", "Projectile motion", 68),
        ("4.5", "Newton’s laws of motion", 72),
        ("4.6", "Momentum", 75),
        ("4.7", "Work, energy and power", 78),
        ("4.8", "Conservation of energy", 80),
        ("4.9", "Bulk properties of solids", 83),
        ("4.10", "The Young modulus", 88),
    ]),
    ("5", "Electricity", 93, [
        ("5.1", "Basics of electricity", 93),
        ("5.2", "Current–voltage characteristics", 95),
        ("5.3", "Common current–voltage characteristics", 96),
        ("5.4", "Resistivity", 96),
        ("5.5", "Circuits", 100),
        ("5.6", "Potential dividers", 105),
        ("5.7", "Electromotive force and internal resistance", 109),
    ]),
    ("6", "Further mechanics and thermal physics", 114, [
        ("6.1", "Periodic motion", 114),
        ("6.2", "Thermal physics", 125),
    ]),
    ("7", "Fields and their consequences", 138, [
        ("7.1", "Fields", 138),
        ("7.2", "Gravitational fields", 138),
        ("7.3", "Electric fields", 144),
        ("7.4", "Capacitance", 147),
        ("7.5", "Magnetic fields", 155),
    ]),
    ("8", "Nuclear physics", 172, [
        ("8.1", "Radioactivity", 172),
    ]),
    ("9", "Astrophysics", 192, [
        ("9.1", "Telescopes", 192),
        ("9.2", "Classification of stars", 198),
        ("9.3", "Cosmology", 207),
    ]),
]

STOP_BEFORE_PRINTED_PAGE = 216  # stop before answers

# =========================================================
# HELPERS
# =========================================================
def printed_to_pdf_index(printed_page: int) -> int:
    return printed_page - 1 + PDF_PAGE_OFFSET


def safe_filename(section_number: str, title: str) -> str:
    title = title.lower().strip()
    title = title.replace("&", "and")
    title = title.replace("–", "-")
    title = title.replace("—", "-")
    title = title.replace("’", "")
    title = re.sub(r"[^\w\s\-.]", "", title)
    title = re.sub(r"\s+", "_", title)
    return f"{section_number}_{title}.txt"


def clean_line(line: str) -> str:
    line = line.strip()

    if not line:
        return ""

    low = line.lower()

    # junk / footer / index-like noise
    if low == "exam practice answers and quick quizzes at www.hoddereducation.co.uk/myrevisionnotes":
        return ""
    if low == "exam practice answers and quick quizzes at":
        return ""
    if low == "my revision planner":
        return ""
    if low == "aqa a-level physics":
        return ""
    if low == "hodder":
        return ""
    if low == "education":
        return ""
    if low == "learn more":
        return ""
    if low == "exam board approved resources":
        return ""
    if low == "our student books and":
        return ""
    if low == "student etextbooks":
        return ""
    if low == "have been selected":
        return ""
    if low == "for aqa’s approval":
        return ""
    if low == "process.":
        return ""
    if low == "216 now test yourself answers":
        return ""
    if low == "224 units, useful formulae and mathematics":
        return ""
    if low == "227 index":
        return ""
    if re.fullmatch(r"\d+", line):
        return ""

    return line


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    cleaned = []
    for line in lines:
        c = clean_line(line)
        if c:
            cleaned.append(c)

    text = "\n".join(cleaned)

    # remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # join some wrapped lines where the next line clearly continues a sentence
    text = re.sub(r"(?<=[a-z,])\n(?=[a-z])", " ", text)

    return text.strip()


def remove_section_heading_from_body(text: str, title: str) -> str:
    lines = text.splitlines()
    if not lines:
        return text

    normalized_title = re.sub(r"\s+", " ", title.strip().lower())
    new_lines = []

    skipped_once = False
    for line in lines:
        candidate = re.sub(r"\s+", " ", line.strip().lower())
        if not skipped_once and candidate == normalized_title:
            skipped_once = True
            continue
        new_lines.append(line)

    return "\n".join(new_lines).strip()


def flatten_sections(sections):
    flat = []
    for chapter_num, chapter_title, chapter_start, subs in sections:
        for sub_num, sub_title, sub_start in subs:
            flat.append({
                "chapter_number": chapter_num,
                "chapter_title": chapter_title,
                "section_number": sub_num,
                "section_title": sub_title,
                "start_page": sub_start,
            })
    return flat


# =========================================================
# MAIN
# =========================================================
os.makedirs(OUTPUT_DIR, exist_ok=True)

doc = fitz.open(PDF_PATH)
flat_sections = flatten_sections(SECTIONS)

for i, section in enumerate(flat_sections):
    start_printed = section["start_page"]

    if i + 1 < len(flat_sections):
        end_printed_exclusive = flat_sections[i + 1]["start_page"]
    else:
        end_printed_exclusive = STOP_BEFORE_PRINTED_PAGE

    start_pdf = printed_to_pdf_index(start_printed)
    end_pdf_exclusive = printed_to_pdf_index(end_printed_exclusive)

    page_texts = []
    actual_pages = []

    for pdf_index in range(start_pdf, end_pdf_exclusive):
        if pdf_index < 0 or pdf_index >= len(doc):
            continue

        page = doc[pdf_index]
        raw = page.get_text("text")
        if raw and raw.strip():
            page_texts.append(raw)
            actual_pages.append(pdf_index + 1)

    if not page_texts:
        print(f"Skipped {section['section_number']} {section['section_title']} (no text found)")
        continue

    combined_text = "\n\n".join(page_texts)
    combined_text = clean_text(combined_text)
    combined_text = remove_section_heading_from_body(combined_text, section["section_title"])

    header = (
        f"[TEXTBOOK: {TEXTBOOK_NAME} | "
        f"CHAPTER: {section['chapter_number']} {section['chapter_title']} | "
        f"SECTION: {section['section_number']} {section['section_title']} | "
        f"PRINTED_PAGES: {start_printed}-{end_printed_exclusive - 1}]"
    )

    final_text = header + "\n\n" + combined_text

    filename = safe_filename(section["section_number"], section["section_title"])
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(final_text)

    print(f"Saved: {filepath}")

doc.close()
print("Done.")