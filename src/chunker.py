from __future__ import annotations


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[str]:
    """
    문자 수 기준 단순 chunking.
    초기 Iteration에서는 디버깅이 쉬운 문자 기준 chunking 사용.
    """
    if not text.strip():
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size는 1 이상이어야 합니다.")

    if overlap < 0:
        raise ValueError("overlap은 0 이상이어야 합니다.")

    if overlap >= chunk_size:
        raise ValueError("overlap은 chunk_size보다 작아야 합니다.")

    chunks: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_len:
            break

        start = end - overlap

    return chunks


def build_chunk_records(
    *,
    inner_zip_name: str,
    xml_name: str,
    document_title: str,
    sections: list[dict],
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[dict]:
    """
    section 목록을 받아 chunk metadata 레코드로 변환.
    """
    records: list[dict] = []

    for section_idx, section in enumerate(sections):
        section_title = section["section_title"]
        section_text = section["section_text"]

        chunks = chunk_text(section_text, chunk_size=chunk_size, overlap=overlap)

        for chunk_idx, chunk in enumerate(chunks):
            records.append(
                {
                    "inner_zip_name": inner_zip_name,
                    "xml_name": xml_name,
                    "document_title": document_title,
                    "section_index": section_idx,
                    "section_title": section_title,
                    "chunk_index": chunk_idx,
                    "chunk_text": chunk,
                    "chunk_length": len(chunk),
                }
            )

    return records