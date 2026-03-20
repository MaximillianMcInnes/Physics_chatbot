import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pathlib import Path

URL = "https://www.savemyexams.com/a-level/physics/aqa/17/revision-notes/"
OUTPUT_ALL = "all_links.txt"
OUTPUT_FILTERED = "revision_links.txt"


def normalise_url(base_url: str, href: str) -> str:
    full_url = urljoin(base_url, href)
    parsed = urlparse(full_url)

    # remove fragments like #section
    clean = parsed._replace(fragment="").geturl()

    # strip trailing slash duplicates except root
    if clean.endswith("/") and len(parsed.path) > 1:
        clean = clean[:-1]

    return clean


def get_all_links(url: str) -> set[str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    links = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href:
            continue

        full_url = normalise_url(url, href)

        # only keep real web pages
        if full_url.startswith(("http://", "https://")):
            links.add(full_url)

    return links


def filter_revision_links(links: set[str], source_url: str) -> list[str]:
    source_domain = urlparse(source_url).netloc

    filtered = []
    for link in links:
        parsed = urlparse(link)

        # keep only same-domain revision-note pages, excluding the base page itself
        if (
            parsed.netloc == source_domain
            and "/revision-notes/" in parsed.path
            and link.rstrip("/") != source_url.rstrip("/")
        ):
            filtered.append(link)

    return sorted(set(filtered))


def save_links(filename: str, links: list[str] | set[str]) -> None:
    Path(filename).write_text("\n".join(sorted(links)), encoding="utf-8")


def main():
    print(f"Scraping links from:\n{URL}\n")

    all_links = get_all_links(URL)
    revision_links = filter_revision_links(all_links, URL)

    print(f"Total links found: {len(all_links)}")
    print(f"Filtered revision links found: {len(revision_links)}\n")

    print("=== FILTERED REVISION LINKS ===")
    for link in revision_links:
        print(link)

    save_links(OUTPUT_ALL, all_links)
    save_links(OUTPUT_FILTERED, revision_links)

    print(f"\nSaved all links to: {OUTPUT_ALL}")
    print(f"Saved filtered revision links to: {OUTPUT_FILTERED}")


if __name__ == "__main__":
    main()