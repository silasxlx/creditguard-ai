from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .models import PolicyChunk, PolicyDocument

RRF_K = 60
MAX_CHUNK_CHARS = 600
CHUNK_OVERLAP = 80


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PolicySource:
    policy_pack_version: str
    title: str
    source_filename: str
    source_hash: str
    text: str


@dataclass(frozen=True)
class PolicyChunkRecord:
    policy_document_id: str
    policy_pack_version: str
    source_filename: str
    source_hash: str
    chunk_id: str
    ordinal: int
    section_path: list[str]
    text: str
    text_hash: str
    locator: dict[str, Any]


@dataclass(frozen=True)
class RetrievalHit:
    query: str
    rule_id: str
    chunk_id: str
    policy_pack_version: str
    section_path: list[str]
    locator: dict[str, Any]
    text: str
    quote_hash: str
    bm25_rank: int | None
    bm25_score: float | None
    dense_rank: int | None
    dense_score: float | None
    rrf_score: float
    rerank_rank: int | None
    rerank_score: float | None
    selected: bool
    index_manifest_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "rule_id": self.rule_id,
            "chunk_id": self.chunk_id,
            "policy_pack_version": self.policy_pack_version,
            "section_path": self.section_path,
            "locator": self.locator,
            "text": self.text,
            "quote_hash": self.quote_hash,
            "bm25_rank": self.bm25_rank,
            "bm25_score": self.bm25_score,
            "dense_rank": self.dense_rank,
            "dense_score": self.dense_score,
            "rrf_score": self.rrf_score,
            "rerank_rank": self.rerank_rank,
            "rerank_score": self.rerank_score,
            "selected": self.selected,
            "index_manifest_hash": self.index_manifest_hash,
        }


class EmbeddingProvider(Protocol):
    model_name: str
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class Reranker(Protocol):
    model_name: str

    def rerank(self, query: str, texts: list[str]) -> list[float]: ...


def tokenize(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", "", text.lower())
    try:
        import jieba

        tokens = [token for token in jieba.lcut(cleaned, cut_all=False) if token.strip()]
    except ImportError:  # pragma: no cover - dependency is locked for runtime
        tokens = re.findall(r"[\u4e00-\u9fff]|[a-z0-9_]+", cleaned)
    return tokens or [cleaned]


def load_policy_sources(root: Path, policy_pack_version: str) -> list[PolicySource]:
    sources: list[PolicySource] = []
    for path in sorted(root.glob("*.md")):
        content = path.read_bytes()
        text = content.decode("utf-8")
        title = next(
            (line[2:].strip() for line in text.splitlines() if line.startswith("# ")), path.stem
        )
        sources.append(
            PolicySource(
                policy_pack_version=policy_pack_version,
                title=title,
                source_filename=path.name,
                source_hash=sha256_bytes(content),
                text=text,
            )
        )
    if len(sources) != 5:
        raise ValueError(f"Expected 5 policy documents, found {len(sources)}")
    return sources


def _section_path(line: str, current: list[str]) -> list[str] | None:
    match = re.match(r"^(#+)\s+(.+?)\s*$", line)
    if not match:
        return None
    level = len(match.group(1))
    path = current[: max(level - 1, 0)]
    path.append(match.group(2))
    return path


def _split_long_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    sentences = [part.strip() for part in re.split(r"(?<=[。；;.!！？])", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for sentence in sentences or [text]:
        if current and len(current) + len(sentence) > max_chars:
            chunks.append(current)
            current = current[-CHUNK_OVERLAP:]
        current += sentence
    if current:
        chunks.append(current)
    return chunks


def chunk_policy(source: PolicySource) -> list[PolicyChunkRecord]:
    chunks: list[PolicyChunkRecord] = []
    section_path: list[str] = []
    buffer: list[str] = []
    buffer_path: list[str] = []

    def flush() -> None:
        nonlocal buffer, buffer_path
        text = "\n".join(buffer).strip()
        if not text:
            buffer = []
            return
        for part in _split_long_text(text):
            ordinal = len(chunks)
            text_hash = sha256_text(part)
            document_id = sha256_text(f"{source.policy_pack_version}|{source.source_hash}")
            chunk_id = sha256_text(
                f"{document_id}|{source.source_hash}|{buffer_path}|{ordinal}|{text_hash}"
            )
            chunks.append(
                PolicyChunkRecord(
                    policy_document_id=document_id,
                    policy_pack_version=source.policy_pack_version,
                    source_filename=source.source_filename,
                    source_hash=source.source_hash,
                    chunk_id=chunk_id,
                    ordinal=ordinal,
                    section_path=list(buffer_path),
                    text=part,
                    text_hash=text_hash,
                    locator={"source_filename": source.source_filename, "ordinal": ordinal},
                )
            )
        buffer = []

    for line in source.text.splitlines():
        path = _section_path(line, section_path)
        if path is not None:
            flush()
            section_path = path
            continue
        if not line.strip():
            flush()
            continue
        if not buffer:
            buffer_path = list(section_path)
        buffer.append(line.strip())
        if len("\n".join(buffer)) >= MAX_CHUNK_CHARS:
            flush()
    flush()
    return chunks


class HashEmbeddingProvider:
    model_name = "hash-embedding-v1"

    def __init__(self, dimension: int = 1024) -> None:
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimension
            for token in tokenize(text):
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                index = int.from_bytes(digest[:4], "big") % self.dimension
                sign = 1.0 if digest[4] % 2 else -1.0
                vector[index] += sign
            norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            vectors.append([value / norm for value in vector])
        return vectors


class DashScopeEmbeddingProvider:
    model_name = "text-embedding-v4"
    dimension = 1024

    def __init__(self, base_url: str, api_key: str, timeout_seconds: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx

        response = httpx.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model_name, "input": texts, "dimensions": self.dimension},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json().get("data", [])
        vectors = [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]
        if len(vectors) != len(texts):
            raise ValueError("Embedding response length does not match request")
        return vectors


class BM25Index:
    def __init__(self, chunks: list[PolicyChunkRecord]) -> None:
        self.chunks = chunks
        self.tokens = [tokenize(chunk.text) for chunk in chunks]
        self.document_frequency: dict[str, int] = {}
        for tokens in self.tokens:
            for token in set(tokens):
                self.document_frequency[token] = self.document_frequency.get(token, 0) + 1
        self.average_length = sum(len(tokens) for tokens in self.tokens) / max(len(self.tokens), 1)

    def search(self, query: str, top_k: int = 30) -> list[tuple[int, float]]:
        query_tokens = tokenize(query)
        total = len(self.tokens)
        scored: list[tuple[int, float]] = []
        for index, tokens in enumerate(self.tokens):
            term_counts = {token: tokens.count(token) for token in set(tokens)}
            score = 0.0
            for token in query_tokens:
                frequency = term_counts.get(token, 0)
                if not frequency:
                    continue
                df = self.document_frequency.get(token, 0)
                idf = math.log(1 + (total - df + 0.5) / (df + 0.5))
                denominator = frequency + 1.5 * (0.25 + 0.75 * len(tokens) / self.average_length)
                score += idf * frequency * 2.5 / denominator
            scored.append((index, score))
        scored.sort(key=lambda item: (-item[1], self.chunks[item[0]].chunk_id))
        return scored[:top_k]


class DenseIndex:
    def __init__(self, chunks: list[PolicyChunkRecord], embedder: EmbeddingProvider) -> None:
        self.chunks = chunks
        self.embedder = embedder
        self.vectors = embedder.embed([chunk.text for chunk in chunks])
        self.faiss_index: Any | None = None
        try:
            import faiss
            import numpy as np

            self.faiss_index = faiss.IndexFlatIP(embedder.dimension)
            self.faiss_index.add(np.asarray(self.vectors, dtype="float32"))
        except ImportError:  # pragma: no cover - exercised only without optional wheels
            self.faiss_index = None

    def search(self, query: str, top_k: int = 30) -> list[tuple[int, float]]:
        query_vector = self.embedder.embed([query])[0]
        if self.faiss_index is not None:
            import numpy as np

            scores, indices = self.faiss_index.search(
                np.asarray([query_vector], dtype="float32"), min(top_k, len(self.chunks))
            )
            result = [
                (int(index), float(score))
                for index, score in zip(indices[0], scores[0], strict=True)
                if index >= 0
            ]
            result.sort(key=lambda item: (-item[1], self.chunks[item[0]].chunk_id))
        else:
            result = [
                (index, sum(left * right for left, right in zip(query_vector, vector, strict=True)))
                for index, vector in enumerate(self.vectors)
            ]
            result.sort(key=lambda item: (-item[1], self.chunks[item[0]].chunk_id))
            result = result[:top_k]
        return result


class LexicalReranker:
    model_name = "qwen3-rerank-mock"

    def rerank(self, query: str, texts: list[str]) -> list[float]:
        query_tokens = set(tokenize(query))
        return [
            sum(1.0 for token in query_tokens if token in set(tokenize(text)))
            + (1.0 if query in text else 0.0)
            for text in texts
        ]


class DashScopeReranker:
    model_name = "qwen3-rerank"

    def __init__(self, base_url: str, api_key: str, timeout_seconds: float = 60.0) -> None:
        normalized = base_url.rstrip("/")
        if normalized.endswith("/compatible-mode/v1"):
            normalized = normalized[: -len("/compatible-mode/v1")] + "/compatible-api/v1"
        self.base_url = normalized
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def rerank(self, query: str, texts: list[str]) -> list[float]:
        import httpx

        response = httpx.post(
            f"{self.base_url}/reranks",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model_name,
                "query": query,
                "documents": texts,
                "top_n": len(texts),
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        scores = [0.0] * len(texts)
        for item in results:
            scores[int(item["index"])] = float(item.get("relevance_score", 0.0))
        return scores


class PolicyIndex:
    def __init__(
        self,
        chunks: list[PolicyChunkRecord],
        embedder: EmbeddingProvider | None = None,
        reranker: Reranker | None = None,
        policy_pack_version: str = "synthetic-v1",
    ) -> None:
        self.chunks = chunks
        self.policy_pack_version = policy_pack_version
        self.embedder = embedder or HashEmbeddingProvider()
        self.reranker = reranker or LexicalReranker()
        self.bm25 = BM25Index(chunks)
        self.dense = DenseIndex(chunks, self.embedder)
        self.manifest_hash = sha256_text(
            "|".join(
                [
                    policy_pack_version,
                    self.embedder.model_name,
                    str(self.embedder.dimension),
                    "normalized=true",
                    "jieba-finance-v1",
                    "|".join(chunk.chunk_id for chunk in chunks),
                ]
            )
        )

    def search(self, query: str, rule_id: str, top_k: int = 5) -> list[RetrievalHit]:
        bm25_results = self.bm25.search(query, 30)
        dense_results = self.dense.search(query, 30)
        bm25_by_id = {
            self.chunks[index].chunk_id: (rank, score)
            for rank, (index, score) in enumerate(bm25_results, start=1)
        }
        dense_by_id = {
            self.chunks[index].chunk_id: (rank, score)
            for rank, (index, score) in enumerate(dense_results, start=1)
        }
        candidate_ids = set(bm25_by_id) | set(dense_by_id)
        ranked_ids = sorted(
            candidate_ids,
            key=lambda chunk_id: (
                -sum(
                    1.0 / (RRF_K + rank)
                    for rank in (
                        bm25_by_id.get(chunk_id, (None, None))[0],
                        dense_by_id.get(chunk_id, (None, None))[0],
                    )
                    if rank is not None
                ),
                min(
                    rank
                    for rank in (
                        bm25_by_id.get(chunk_id, (None, None))[0],
                        dense_by_id.get(chunk_id, (None, None))[0],
                    )
                    if rank is not None
                ),
                chunk_id,
            ),
        )[:20]
        chunk_by_id = {chunk.chunk_id: chunk for chunk in self.chunks}
        rerank_scores = self.reranker.rerank(query, [chunk_by_id[item].text for item in ranked_ids])
        reranked = sorted(
            zip(ranked_ids, rerank_scores, strict=True),
            key=lambda item: (-item[1], item[0]),
        )
        rerank_rank = {chunk_id: rank for rank, (chunk_id, _) in enumerate(reranked, start=1)}
        rerank_score = {chunk_id: score for chunk_id, score in reranked}
        hits: list[RetrievalHit] = []
        for chunk_id in ranked_ids:
            chunk = chunk_by_id[chunk_id]
            bm25_rank, bm25_score = bm25_by_id.get(chunk_id, (None, None))
            dense_rank, dense_score = dense_by_id.get(chunk_id, (None, None))
            rrf_score = sum(
                1.0 / (RRF_K + rank) for rank in (bm25_rank, dense_rank) if rank is not None
            )
            hits.append(
                RetrievalHit(
                    query=query,
                    rule_id=rule_id,
                    chunk_id=chunk_id,
                    policy_pack_version=chunk.policy_pack_version,
                    section_path=chunk.section_path,
                    locator=chunk.locator,
                    text=chunk.text,
                    quote_hash=chunk.text_hash,
                    bm25_rank=bm25_rank,
                    bm25_score=bm25_score,
                    dense_rank=dense_rank,
                    dense_score=dense_score,
                    rrf_score=rrf_score,
                    rerank_rank=rerank_rank[chunk_id],
                    rerank_score=rerank_score[chunk_id],
                    selected=rerank_rank[chunk_id] <= top_k,
                    index_manifest_hash=self.manifest_hash,
                )
            )
        return hits


def build_policy_index(
    root: Path,
    policy_pack_version: str = "synthetic-v1",
    embedder: EmbeddingProvider | None = None,
    reranker: Reranker | None = None,
) -> PolicyIndex:
    sources = load_policy_sources(root, policy_pack_version)
    chunks = [chunk for source in sources for chunk in chunk_policy(source)]
    return PolicyIndex(
        chunks, embedder=embedder, reranker=reranker, policy_pack_version=policy_pack_version
    )


def persist_policy_index(db: Any, index: PolicyIndex, root: Path) -> None:
    for source in load_policy_sources(root, index.policy_pack_version):
        document_id = sha256_text(f"{source.policy_pack_version}|{source.source_hash}")
        document = db.get(PolicyDocument, document_id)
        if document is None:
            document = PolicyDocument(
                id=document_id,
                policy_pack_version=source.policy_pack_version,
                title=source.title,
                source_filename=source.source_filename,
                source_hash=source.source_hash,
                metadata_json={"source_type": "synthetic_markdown_extract"},
            )
            db.add(document)
    db.flush()
    for chunk in index.chunks:
        if db.query(PolicyChunk).filter(PolicyChunk.chunk_id == chunk.chunk_id).first() is None:
            db.add(
                PolicyChunk(
                    id=chunk.chunk_id,
                    policy_document_id=chunk.policy_document_id,
                    policy_pack_version=chunk.policy_pack_version,
                    chunk_id=chunk.chunk_id,
                    source_hash=chunk.source_hash,
                    ordinal=chunk.ordinal,
                    section_path=chunk.section_path,
                    text=chunk.text,
                    text_hash=chunk.text_hash,
                    locator=chunk.locator,
                )
            )
    db.flush()


__all__ = [
    "BM25Index",
    "DashScopeEmbeddingProvider",
    "DashScopeReranker",
    "DenseIndex",
    "HashEmbeddingProvider",
    "LexicalReranker",
    "PolicyChunkRecord",
    "PolicyIndex",
    "RetrievalHit",
    "build_policy_index",
    "chunk_policy",
    "load_policy_sources",
    "persist_policy_index",
]
