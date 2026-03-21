from dotenv import load_dotenv

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from config import VECTORSTORE_DIR, COLLECTION_NAME, EMBEDDING_MODEL

load_dotenv()


def format_source(meta: dict) -> str:
    source_type = meta.get("source_type", "unknown")

    if source_type == "textbook":
        return (
            f'[TEXTBOOK] {meta.get("chapter", "Unknown chapter")} | '
            f'{meta.get("section", "Unknown section")} | '
            f'pp. {meta.get("printed_pages", "?")}'
        )

    if source_type == "savemyexams":
        return (
            f'[SAVE MY EXAMS] {meta.get("heading", "Unknown heading")} | '
            f'{meta.get("url", "No link")}'
        )

    if source_type == "spec":
        bits = [meta.get("topic"), meta.get("section"), meta.get("subsection")]
        bits = [b for b in bits if b]
        return "[SPEC] " + " | ".join(bits) if bits else "[SPEC] Unknown section"

    return "[UNKNOWN SOURCE]"


def main() -> None:
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(VECTORSTORE_DIR),
    )

    while True:
        query = input("\nQuery (or 'exit'): ").strip()
        if query.lower() == "exit":
            break

        results = vectorstore.similarity_search_with_score(query, k=5)

        for i, (doc, score) in enumerate(results, start=1):
            print("\n" + "=" * 100)
            print(f"Result {i} | score={score}")
            print(format_source(doc.metadata))
            print("-" * 100)
            print(doc.page_content[:900])
            print("=" * 100)


if __name__ == "__main__":
    main()