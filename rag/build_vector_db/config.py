from pathlib import Path

# Project root = go up from rag/build_vector_db/config.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data_collection" / "data"
TEXTBOOK_DIR = DATA_DIR / "textbook_sections"
SAVEMYEXAMS_DIR = DATA_DIR / "savemyexams_pages"
SPEC_DIR = DATA_DIR / "spec_split"

VECTORSTORE_DIR = PROJECT_ROOT / "rag" / "vectorstore" / "physics_chroma"

COLLECTION_NAME = "aqa_physics_rag"

# Embeddings
EMBEDDING_MODEL = "text-embedding-3-large"

# Helpful if you want cheaper embeddings later:
# EMBEDDING_MODEL = "text-embedding-3-small"