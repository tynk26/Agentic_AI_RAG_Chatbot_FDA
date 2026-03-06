from __future__ import annotations

from lxml import etree
from io import BytesIO
from src.utils import safe_text


def parse_spl_xml(xml_text: str) -> dict:
    """
    FDA SPL XML에서 기초 메타데이터와 전체 텍스트를 추출합니다.
    Iteration 1 목적:
    - 안정적으로 XML 파싱
    - 제목/ID 일부 추출
    - 전체 텍스트 평탄화
    """
    parser = etree.XMLParser(recover=True, huge_tree=True)
    root = etree.parse(BytesIO(xml_text.encode("utf-8")), parser).getroot()

    # XML namespace 무시용 xpath
    def xpath_text(expr: str) -> list[str]:
        results = root.xpath(expr)
        cleaned: list[str] = []
        for item in results:
            if isinstance(item, str):
                val = safe_text(item)
            else:
                val = safe_text(getattr(item, "text", ""))
            if val:
                cleaned.append(val)
        return cleaned

    # 가능한 메타데이터 후보들
    titles = xpath_text("//*[local-name()='title']/text()")
    ids = xpath_text("//*[local-name()='id']/@root")
    codes = xpath_text("//*[local-name()='code']/@displayName")

    # 전체 텍스트 평탄화
    all_text_nodes = root.xpath("//text()")
    flattened_parts = []
    for node in all_text_nodes:
        val = safe_text(str(node))
        if val:
            flattened_parts.append(val)

    full_text = "\n".join(flattened_parts)

    return {
        "title": titles[0] if titles else "제목 미확인",
        "document_id": ids[0] if ids else "문서 ID 미확인",
        "code_display": codes[0] if codes else "코드 미확인",
        "text_length": len(full_text),
        "preview": full_text[:3000],
        "full_text": full_text,
    }