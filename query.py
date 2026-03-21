import os
import re
from typing import Dict, List, Tuple, Any

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

from rag.build_vector_db.config import (
    VECTORSTORE_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
)
from rag.inference.prompts import SYSTEM_PROMPT, build_user_prompt


load_dotenv()

# ============================================================
# Config
# ============================================================
# Keep configurable so you can swap gpt-5.2 <-> gpt-5.4 easily.
LLM_MODEL = os.getenv("RAG_LLM_MODEL", "gpt-5.2")
TOP_K = int(os.getenv("RAG_TOP_K", "6"))

# Optional simple weighting at rerank stage
BOOST_TEXTBOOK = 0.08
BOOST_SPEC = 0.05
BOOST_SME = 0.03


# ============================================================
# Citation helpers
# ============================================================
def citation_from_metadata(meta: Dict[str, Any]) -> str:
    source_type = meta.get("source_type", "unknown")

    if source_type == "textbook":
        book = meta.get("book") or "Unknown textbook"
        chapter = meta.get("chapter") or "Unknown chapter"
        section = meta.get("section") or "Unknown section"
        pages = meta.get("printed_pages") or "?"
        return f"Textbook: {book} | {chapter} | {section} | pp. {pages}"

    if source_type == "savemyexams":
        heading = meta.get("heading") or meta.get("file_name") or "Unknown page"
        url = meta.get("url") or "No URL"
        return f"Save My Exams: {heading} | {url}"

    if source_type == "spec":
        parts = [
            meta.get("spec"),
            meta.get("topic"),
            meta.get("section"),
            meta.get("subsection"),
        ]
        parts = [p for p in parts if p]
        if parts:
            return "Spec: " + " | ".join(parts)
        return "Spec: Unknown section"

    return f"Unknown source: {meta.get('file_name', 'unknown file')}"


def short_source_kind(meta: Dict[str, Any]) -> str:
    source_type = meta.get("source_type", "unknown")
    if source_type == "textbook":
        return "textbook"
    if source_type == "savemyexams":
        return "savemyexams"
    if source_type == "spec":
        return "spec"
    return "unknown"


def format_context(docs: List[Any]) -> str:
    """
    Builds the prompt context using explicit Source numbers.
    """
    blocks = []

    for i, doc in enumerate(docs, start=1):
        citation = citation_from_metadata(doc.metadata)
        source_kind = short_source_kind(doc.metadata)
        content = doc.page_content.strip()

        blocks.append(
            f"[Source {i}]\n"
            f"Type: {source_kind}\n"
            f"Citation: {citation}\n"
            f"Content:\n{content}"
        )

    return "\n\n" + ("\n\n" + ("-" * 100) + "\n\n").join(blocks)


def extract_used_source_numbers(answer_text: str) -> List[int]:
    """
    Finds [Source 1], [Source 2], etc.
    """
    nums = re.findall(r"\[Source\s+(\d+)\]", answer_text)
    used = sorted({int(n) for n in nums})
    return used


def build_sources_section_from_used_numbers(answer_text: str, docs: List[Any]) -> str:
    used_numbers = extract_used_source_numbers(answer_text)

    if not used_numbers:
        return "Sources\n- No sources explicitly cited."

    lines = ["Sources"]
    for n in used_numbers:
        if 1 <= n <= len(docs):
            citation = citation_from_metadata(docs[n - 1].metadata)
            lines.append(f"- [Source {n}] {citation}")

    return "\n".join(lines)


def strip_existing_sources_section(text: str) -> str:
    """
    Removes any LLM-generated Sources section so we can replace it
    with a guaranteed-correct one based on actual cited source numbers.
    """
    pattern = re.compile(r"\nSources\s*\n.*$", re.DOTALL)
    return re.sub(pattern, "", text).strip()


# ============================================================
# Vector store
# ============================================================
def get_vectorstore() -> Chroma:
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(VECTORSTORE_DIR),
    )


def rerank_docs(query: str, docs_with_scores: List[Tuple[Any, float]]) -> List[Any]:
    """
    Chroma similarity_search_with_score returns lower distance = better.
    We lightly boost textbook/spec/SME for nicer source balance.
    """
    reranked = []

    query_lower = query.lower()

    for doc, score in docs_with_scores:
        adjusted = score
        source_type = doc.metadata.get("source_type")

        if source_type == "textbook":
            adjusted -= BOOST_TEXTBOOK
        elif source_type == "spec":
            adjusted -= BOOST_SPEC
        elif source_type == "savemyexams":
            adjusted -= BOOST_SME

        # tiny keyword nudges
        title_bits = " ".join(
            str(doc.metadata.get(k, "") or "")
            for k in ["chapter", "section", "subsection", "heading", "topic"]
        ).lower()

        if any(word in title_bits for word in query_lower.split()):
            adjusted -= 0.02

        reranked.append((doc, adjusted))

    reranked.sort(key=lambda x: x[1])
    return [doc for doc, _ in reranked]


def retrieve_docs(query: str, k: int = TOP_K) -> List[Any]:
    vectorstore = get_vectorstore()
    docs_with_scores = vectorstore.similarity_search_with_score(query, k=k)
    return rerank_docs(query, docs_with_scores)


# ============================================================
# LLM
# ============================================================
def get_llm() -> ChatOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not found in .env")

    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=0,
    )


def build_messages(question: str, docs: List[Any]) -> List[Dict[str, str]]:
    context = format_context(docs)

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(question, context)},
    ]


def generate_answer(question: str, docs: List[Any]) -> str:
    llm = get_llm()
    messages = build_messages(question, docs)
    response = llm.invoke(messages)

    raw_text = response.content if isinstance(response.content, str) else str(response.content)
    main_answer = strip_existing_sources_section(raw_text)
    canonical_sources = build_sources_section_from_used_numbers(main_answer, docs)

    return f"{main_answer}\n\n{canonical_sources}"


def answer_question(question: str, k: int = TOP_K) -> Tuple[str, List[Any]]:
    docs = retrieve_docs(question, k=k)

    if not docs:
        return "I could not retrieve any relevant sources.\n\nSources\n- No sources retrieved.", []

    answer = generate_answer(question, docs)
    return answer, docs


# ============================================================
# CLI
# ============================================================
def main() -> None:
    print("=" * 100)
    print("AQA Physics RAG Query")
    print(f"Model: {LLM_MODEL}")
    print(f"Top-K: {TOP_K}")
    print("=" * 100)

    while True:
        question = input("\nAsk a question (or type 'exit'): ").strip()
        if question.lower() == "exit":
            break

        if not question:
            continue

        try:
            answer, docs = answer_question(question, k=TOP_K)

            print("\n" + "=" * 100)
            print("ANSWER")
            print("=" * 100)
            print(answer)

            print("\n" + "=" * 100)
            print("RETRIEVED SOURCES")
            print("=" * 100)
            for i, doc in enumerate(docs, start=1):
                print(f"[Source {i}] {citation_from_metadata(doc.metadata)}")

        except Exception as e:
            print(f"\n[ERROR] {e}")


if __name__ == "__main__":
    main()