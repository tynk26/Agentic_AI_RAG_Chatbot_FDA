from __future__ import annotations

import re


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_into_sentence_like_units(text: str) -> list[str]:
    """
    완전한 NLP 문장분리는 아니지만, FDA 라벨 텍스트를
    문장/줄 단위 비슷한 조각으로 나눈다.
    """
    text = normalize_whitespace(text)
    if not text:
        return []

    raw_parts = re.split(r"(?<=[\.\!\?\:;])\s+|\n+", text)
    parts = [part.strip() for part in raw_parts if part.strip()]
    return parts


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[str]:
    """
    문자 수 고정 자르기 대신,
    문장/줄 비슷한 단위들을 누적해서 청크를 만든다.
    오버랩은 문자 기준으로 마지막 일부를 다음 청크에 이어붙인다.
    """
    if not text.strip():
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size는 1 이상이어야 합니다.")

    if overlap < 0:
        raise ValueError("overlap은 0 이상이어야 합니다.")

    if overlap >= chunk_size:
        raise ValueError("overlap은 chunk_size보다 작아야 합니다.")

    units = split_into_sentence_like_units(text)
    if not units:
        return []

    chunks: list[str] = []
    current_units: list[str] = []
    current_len = 0

    for unit in units:
        unit_len = len(unit)

        # 매우 긴 단일 unit는 강제로 분할
        if unit_len > chunk_size:
            if current_units:
                chunk = " ".join(current_units).strip()
                if chunk:
                    chunks.append(chunk)
                current_units = []
                current_len = 0

            start = 0
            while start < unit_len:
                end = min(start + chunk_size, unit_len)
                piece = unit[start:end].strip()
                if piece:
                    chunks.append(piece)
                if end >= unit_len:
                    break
                start = max(end - overlap, start + 1)
            continue

        projected_len = current_len + (1 if current_units else 0) + unit_len

        if projected_len <= chunk_size:
            current_units.append(unit)
            current_len = projected_len
        else:
            chunk = " ".join(current_units).strip()
            if chunk:
                chunks.append(chunk)

            # 오버랩: 직전 chunk의 끝부분 일부를 다음 시작에 반영
            overlap_seed = ""
            if overlap > 0 and chunks:
                overlap_seed = chunks[-1][-overlap:].strip()

            current_units = [overlap_seed, unit] if overlap_seed else [unit]
            current_units = [x for x in current_units if x]
            current_len = len(" ".join(current_units))

    if current_units:
        chunk = " ".join(current_units).strip()
        if chunk:
            chunks.append(chunk)

    # 후처리: 너무 작은 마지막 chunk를 이전 chunk에 합침
    if len(chunks) >= 2 and len(chunks[-1]) < max(120, chunk_size // 5):
        merged = f"{chunks[-2]} {chunks[-1]}".strip()
        chunks = chunks[:-2] + [merged]

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