from __future__ import annotations

from io import BytesIO
from lxml import etree


NS = {"hl7": "urn:hl7-org:v3"}


def safe_text(text: str | None) -> str:
    if text is None:
        return ""
    return " ".join(str(text).split())


def join_non_empty(parts: list[str], sep: str = "\n") -> str:
    cleaned = [safe_text(p) for p in parts if safe_text(p)]
    return sep.join(cleaned)


def get_first_text(node, xpath_expr: str) -> str:
    values = node.xpath(xpath_expr, namespaces=NS)
    if not values:
        return ""
    if isinstance(values[0], str):
        return safe_text(values[0])
    return safe_text(getattr(values[0], "text", ""))


def extract_paragraph_texts(text_node) -> list[str]:
    paragraphs: list[str] = []

    for p in text_node.xpath(".//hl7:paragraph", namespaces=NS):
        text = " ".join(t.strip() for t in p.xpath(".//text()") if safe_text(t))
        text = safe_text(text)
        if text:
            paragraphs.append(text)

    return paragraphs


def extract_list_texts(text_node) -> list[str]:
    blocks: list[str] = []

    for lst in text_node.xpath(".//hl7:list", namespaces=NS):
        items = []
        for item in lst.xpath("./hl7:item", namespaces=NS):
            item_text = " ".join(t.strip() for t in item.xpath(".//text()") if safe_text(t))
            item_text = safe_text(item_text)
            if item_text:
                items.append(f"- {item_text}")

        if items:
            blocks.append("\n".join(items))

    return blocks


def extract_direct_text_fallback(text_node) -> list[str]:
    raw_text = " ".join(t.strip() for t in text_node.xpath(".//text()") if safe_text(t))
    raw_text = safe_text(raw_text)
    return [raw_text] if raw_text else []


def extract_text_blocks(section_node) -> list[str]:
    text_nodes = section_node.xpath("./hl7:text", namespaces=NS)
    if not text_nodes:
        return []

    text_node = text_nodes[0]
    blocks: list[str] = []

    paragraphs = extract_paragraph_texts(text_node)
    list_blocks = extract_list_texts(text_node)

    if paragraphs:
        blocks.extend(paragraphs)

    if list_blocks:
        blocks.extend(list_blocks)

    if not blocks:
        blocks.extend(extract_direct_text_fallback(text_node))

    return [b for b in blocks if safe_text(b)]


def parse_section_recursive(
    section_node,
    *,
    parent_titles: list[str],
) -> list[dict]:
    current_title = get_first_text(section_node, "./hl7:title//text()")
    current_title = current_title if current_title else "무제 섹션"

    code = get_first_text(section_node, "./hl7:code/@code")
    code_display = get_first_text(section_node, "./hl7:code/@displayName")
    section_id = get_first_text(section_node, "./hl7:id/@root")

    hierarchy = [*parent_titles, current_title]
    text_blocks = extract_text_blocks(section_node)

    records: list[dict] = []

    # 현재 섹션 record
    if text_blocks:
        records.append(
            {
                "section_title": parent_titles[0] if parent_titles else current_title,
                "subsection_title": current_title if parent_titles else "",
                "hierarchy_titles": hierarchy,
                "section_id": section_id,
                "loinc_code": code,
                "loinc_display": code_display,
                "text_blocks": text_blocks,
            }
        )

    # nested subsection들 재귀 처리
    child_sections = section_node.xpath("./hl7:component/hl7:section", namespaces=NS)
    for child in child_sections:
        records.extend(
            parse_section_recursive(
                child,
                parent_titles=hierarchy,
            )
        )

    return records


def parse_spl_xml_structured(xml_text: str) -> dict:
    parser = etree.XMLParser(recover=True, huge_tree=True)
    root = etree.parse(BytesIO(xml_text.encode("utf-8")), parser).getroot()

    document_id = get_first_text(root, "//*[local-name()='id'][1]/@root")
    code_display = get_first_text(root, "//*[local-name()='code'][1]/@displayName")

    title_parts = root.xpath("//*[local-name()='title'][1]//text()")
    title = safe_text(" ".join([t for t in title_parts if safe_text(t)]))
    if not title:
        title = "제목 미확인"

    sections: list[dict] = []
    top_sections = root.xpath(
        "./hl7:component/hl7:structuredBody/hl7:component/hl7:section",
        namespaces=NS,
    )

    for sec in top_sections:
        sections.extend(parse_section_recursive(sec, parent_titles=[]))

    return {
        "title": title,
        "document_id": document_id if document_id else "문서 ID 미확인",
        "code_display": code_display if code_display else "코드 미확인",
        "sections": sections,
    }