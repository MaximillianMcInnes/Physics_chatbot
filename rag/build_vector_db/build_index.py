import hashlib
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from tqdm import tqdm

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from config import (
    TEXTBOOK_DIR,
    SAVEMYEXAMS_DIR,
    SPEC_DIR,
    VECTORSTORE_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
)
from parsers import parse_file


load_dotenv()


def make_doc_id(source_type: str, file_name: str) -> str:
    raw = f"{source_type}::{file_name}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_docs_from_folder(folder: Path, source_type: str) -> List[Document]:
    docs: List[Document] = []

    if not folder.exists():
        print(f"[WARN] Folder not found: {folder}")
        return docs

    files = sorted(folder.rglob("*.txt"))
    print(f"[INFO] Loading {len(files)} files from {folder}")

    for path in tqdm(files, desc=f"Parsing {source_type}"):
        body, metadata = parse_file(path, source_type)

        if not body.strip():
            continue

        doc_id = make_doc_id(source_type, path.name)

        metadata = {
            **metadata,
            "doc_id": doc_id,
        }

        docs.append(
            Document(
                page_content=body,
                metadata=metadata,
            )
        )

    return docs


def main() -> None:
    all_docs: List[Document] = []
    all_docs.extend(load_docs_from_folder(TEXTBOOK_DIR, "textbook"))
    all_docs.extend(load_docs_from_folder(SAVEMYEXAMS_DIR, "savemyexams"))
    all_docs.extend(load_docs_from_folder(SPEC_DIR, "spec"))

    if not all_docs:
        raise RuntimeError("No documents found. Check your data folders.")

    print(f"[INFO] Total documents to embed: {len(all_docs)}")

    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(VECTORSTORE_DIR),
    )

    ids = [doc.metadata["doc_id"] for doc in all_docs]
    vectorstore.add_documents(documents=all_docs, ids=ids)

    print(f"[DONE] Vector DB built at: {VECTORSTORE_DIR}")
    print(f"[DONE] Collection: {COLLECTION_NAME}")
    print(f"[DONE] Embedded docs: {len(all_docs)}")


if __name__ == "__main__":
    main()