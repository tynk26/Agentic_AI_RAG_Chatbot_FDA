from __future__ import annotations


def build_context_block(search_results: list[dict], max_items: int = 3) -> str:
    selected = search_results[:max_items]
    parts = []

    for row in selected:
        parts.append(
            f"[문서: {row['document_title']}] "
            f"[섹션: {row['section_title']}] "
            f"{row['chunk_text']}"
        )

    return "\n\n".join(parts)


def generate_korean_answer(question: str, search_results: list[dict]) -> str:
    if not search_results:
        return "관련 근거 청크를 찾지 못했습니다."

    top = search_results[0]
    section_title = top["section_title"]
    document_title = top["document_title"]
    context = build_context_block(search_results, max_items=3)

    answer_lines = [
        f"질문: {question}",
        "",
        "답변 초안:",
        f"가장 관련성이 높은 근거는 '{document_title}' 문서의 '{section_title}' 섹션에서 확인되었습니다.",
        "아래는 검색된 상위 근거를 바탕으로 정리한 내용입니다.",
        "",
        context[:1800],
        "",
        "주의:",
        "- 이 답변은 현재 검색된 FDA SPL 청크를 기반으로 자동 요약한 초안입니다.",
        "- 최종 판단 전에는 원문 섹션과 전체 라벨 문서를 함께 확인하는 것이 좋습니다.",
    ]

    return "\n".join(answer_lines)