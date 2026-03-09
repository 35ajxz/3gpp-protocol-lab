from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

from common import CORPUS_SLICE_DIR, RETRIEVAL_OUTPUT_DIR, ensure_dirs, write_json


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in text.replace("(", " ").replace(")", " ").replace(",", " ").split()]


def build_documents() -> list[dict[str, object]]:
    docs = []
    for path in sorted(CORPUS_SLICE_DIR.glob("*.md")):
        text = path.read_text()
        tokens = tokenize(text)
        docs.append(
            {
                "path": path,
                "text": text,
                "tokens": tokens,
                "tf": Counter(tokens),
            }
        )
    return docs


def rank_query(query: str) -> dict[str, object]:
    docs = build_documents()
    query_tokens = tokenize(query)
    doc_count = max(len(docs), 1)
    df = Counter()
    for doc in docs:
        for token in set(doc["tokens"]):
            df[token] += 1

    results = []
    for doc in docs:
        score = 0.0
        for token in query_tokens:
            if doc["tf"][token]:
                idf = math.log((1 + doc_count) / (1 + df[token])) + 1.0
                score += doc["tf"][token] * idf
        if score > 0:
            results.append(
                {
                    "slice": doc["path"].name,
                    "score": round(score, 3),
                    "preview": " ".join(doc["text"].split())[:220],
                }
            )
    results.sort(key=lambda item: item["score"], reverse=True)
    payload = {"query": query, "results": results}
    return payload


def main() -> None:
    ensure_dirs()
    query = " ".join(sys.argv[1:]).strip() or "RRC resume fullConfig"
    payload = rank_query(query)
    output_path = RETRIEVAL_OUTPUT_DIR / "last_query.json"
    write_json(output_path, payload)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
