"""Build page-traceable chunk artifacts from the searchable data/data.pdf."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter"))

from src.chunking import by_paragraph, fixed_size
from src.ingestion import load_pdf


SOURCE = ROOT / "data" / "data.pdf"
SOURCE_LABEL = "data/data.pdf"
DOC_ID = "arxiv-1204.0653-v1"
RESULTS = ROOT / "results"
META_PATH = ROOT / "data" / "data_pdf_page_metadata.json"


def section_for(page):
    if page == 1:
        return "front_matter"
    if page <= 4:
        return "introduction"
    if page <= 6:
        return "hamilton_jacobi_and_path_integral"
    if page <= 10:
        return "schrodinger_path_amplitude"
    if page <= 16:
        return "de_broglie_and_wave_particle_duality"
    if page <= 19:
        return "operators_and_eigenstates"
    if page <= 24:
        return "schrodinger_derivations"
    if page <= 27:
        return "summary_and_discussion"
    if page == 28:
        return "summary_and_references"
    return "references"


def json_chunk(chunk):
    return {
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "source": chunk.source,
        "page": chunk.page,
        "text": chunk.text,
        "metadata": chunk.metadata,
    }


def main():
    print("| Stage | Progress | Details |", flush=True)
    print("|---|---:|---|", flush=True)
    print("| Parse PDF | 0% | Opening data/data.pdf |", flush=True)
    pages = load_pdf(SOURCE, DOC_ID, SOURCE_LABEL)
    for page in pages:
        page.metadata.update({
            "section": section_for(page.page),
            "page_type": "references" if page.page >= 29 else ("front_matter" if page.page == 1 else "content"),
            "language": "en",
            "document_type": "research_preprint",
        })

    page_metadata = {
        str(page.page): {k: page.metadata[k] for k in ("section", "page_type", "language", "document_type")}
        for page in pages
    }
    META_PATH.write_text(json.dumps(page_metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"| Parse PDF | 100% | {len(pages)} pages, {sum(len(p.text) for p in pages):,} extracted characters |", flush=True)

    print("| Chunk A | 0% | 500 characters, overlap 50 |", flush=True)
    strategies = {
        "A": [chunk for page in pages for chunk in fixed_size(page, 500, 50)],
    }
    print(f"| Chunk A | 100% | {len(strategies['A'])} chunks |", flush=True)
    print("| Chunk B | 0% | Paragraph/block aware, max 500 characters |", flush=True)
    strategies["B"] = [chunk for page in pages for chunk in by_paragraph(page, 500)]
    print(f"| Chunk B | 100% | {len(strategies['B'])} chunks |", flush=True)
    # C shares B's chunks and changes only the metadata filter at query time.
    strategies["C"] = strategies["B"]
    print(f"| Chunk C | 100% | Reuses B chunks; section/page_type filter metadata attached |", flush=True)

    stats = {
        "source": SOURCE_LABEL,
        "document_id": DOC_ID,
        "physical_pages": len(pages),
        "content_pages_counted": 28,
        "content_page_rule": "Pages 1-28 contain title/abstract and the article; pages 29-30 are bibliography-only and excluded from the 30-content-page requirement.",
        "content_requirement_met": False,
        "total_extracted_characters": sum(len(page.text) for page in pages),
        "page_characters": {str(page.page): len(page.text) for page in pages},
        "strategies": {},
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    for name, chunks in strategies.items():
        output = RESULTS / f"chunks_{name}.json"
        output.write_text(json.dumps([json_chunk(c) for c in chunks], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        lengths = [len(c.text) for c in chunks]
        stats["strategies"][name] = {
            "chunk_count": len(chunks),
            "characters": sum(lengths),
            "min_length": min(lengths) if lengths else 0,
            "max_length": max(lengths) if lengths else 0,
            "mean_length": round(sum(lengths) / len(lengths), 1) if lengths else 0,
            "file": f"results/chunks_{name}.json",
        }
    (RESULTS / "chunk_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("| Write chunk files | 100% | results/chunks_A.json, chunks_B.json, chunks_C.json |", flush=True)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
