import re
import requests
from bs4 import BeautifulSoup

#URL = "https://www.savemyexams.com/a-level/physics/aqa/17/revision-notes/1-measurements-and-their-errors/1-1-use-of-si-units-and-their-prefixes/1-1-1-si-units/"


def clean_text_lines(lines):
    cleaned = []
    seen = set()

    for line in lines:
        line = " ".join(line.split()).strip()
        if not line:
            continue
        if line in seen:
            continue
        seen.add(line)
        cleaned.append(line)

    return cleaned


def get_best_heading(soup):
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(" ", strip=True)

    if soup.title:
        return soup.title.get_text(" ", strip=True)

    return "No heading found"


def get_main_container(soup):
    selectors = [
        "main",
        "article",
        '[role="main"]',
        ".revision-note",
        ".content",
        ".article",
        ".post-content",
        ".note",
    ]

    for selector in selectors:
        container = soup.select_one(selector)
        if container:
            return container

    return soup.body


def should_stop(line: str) -> bool:
    lower = line.lower()

    stop_markers = [
        "unlock more, it's free",
        "join the 100,000",
        "students that",
        "read more reviews",
        "test yourself",
        "was this revision note helpful",
        "next:",
    ]

    return any(marker in lower for marker in stop_markers)


def is_breadcrumb_or_page_junk(line: str, heading: str) -> bool:
    lower = line.lower()
    heading_lower = heading.lower()

    junk_starts = [
        "a level physics aqa revision notes",
        "a level",
        "physics",
        "aqa",
        "revision notes",
        "measurements & their errors",
        "use of si units & their prefixes",
        "exam code:",
        "written by:",
        "reviewed by:",
        "updated on",
    ]

    if lower == heading_lower.lower():
        return True

    if lower == heading_lower.replace(": revision note", "").strip():
        return True

    if any(lower.startswith(j) for j in junk_starts):
        return True

    return False


def find_start_index(lines, heading):
    priority_starts = [
        "did this video help you?",
        "si base quantities",
    ]

    lowered = [line.lower() for line in lines]

    for marker in priority_starts:
        for i, line in enumerate(lowered):
            if marker in line:
                return i

    for i, line in enumerate(lowered):
        if heading.lower() in line:
            return i + 1

    return 0


def trim_repeated_prefix(line: str) -> str:
    # Example:
    # "SI Base Quantities There is a seemingly endless number..."
    # -> keep as-is unless the heading is repeated twice etc.
    words = line.split()
    if len(words) >= 6:
        half = len(words) // 2
        first = " ".join(words[:half]).strip().lower()
        second = " ".join(words[half:]).strip().lower()
        if first == second:
            return " ".join(words[:half]).strip()
    return line


def get_filtered_text(soup, heading):
    container = get_main_container(soup)
    if container is None:
        return []

    for tag in container(["script", "style", "noscript", "svg", "img", "button"]):
        tag.decompose()

    raw_lines = []
    for tag in container.find_all(["h1", "h2", "h3", "h4", "p", "li", "div", "span"]):
        text = tag.get_text(" ", strip=True)
        if text:
            raw_lines.append(text)

    lines = clean_text_lines(raw_lines)

    start_idx = find_start_index(lines, heading)
    lines = lines[start_idx:]

    filtered = []
    for line in lines:
        line = trim_repeated_prefix(line)

        if should_stop(line):
            break

        if is_breadcrumb_or_page_junk(line, heading):
            continue

        filtered.append(line)

    return clean_text_lines(filtered)


def scrape_page(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    heading = get_best_heading(soup)
    text_lines = get_filtered_text(soup, heading)

    return {
        "url": url,
        "heading": heading,
        "text_lines": text_lines,
    }

def fetch_urls():
    urls = []
    links_Text = r"D:\coding_shit\Physics_chatbot\data_collection\revision_links.txt"
    #use abs path because i am a goon
    with open(links_Text, "r") as file:
        for url in file:
            urls.append(url.strip())
    return urls

def main():
    articles = fetch_urls()
    for urls in articles:
        data = scrape_page(urls)
        name = urls.split("revision-notes/")[1]
        name = name.replace("/", "_")
        name = f"D:/coding_shit/Physics_chatbot/data_collection/data/savemyexams_pages/savemyexams_{name}.txt"
        


        print("=" * 100)
        print(f"LINK: {data['url']}")
        print(f"HEADING: {data['heading']}")
        print("=" * 100)
        print()
        for line in data["text_lines"]:
            print(line)

        with open(name, "w", encoding="utf-8") as f:
            f.write(f"LINK: {data['url']}\n")
            f.write(f"HEADING: {data['heading']}\n")
            f.write("=" * 100 + "\n\n")
            for line in data["text_lines"]:
                f.write(line + "\n")


if __name__ == "__main__":
    main()