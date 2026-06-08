from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.rag_service import build_rag_service, default_rag_settings


def main() -> None:
    settings = default_rag_settings()
    service = build_rag_service(settings=settings)

    print("Vector index rebuilt successfully")
    print(f"Data directory: {settings.data_dir}")
    print(f"Persist directory: {service.persist_dir}")
    print(f"Collection: {service.collection_name}")
    print(f"Documents loaded: {service.document_count}")
    print(f"Chunks indexed: {service.chunk_count}")


if __name__ == "__main__":
    main()
