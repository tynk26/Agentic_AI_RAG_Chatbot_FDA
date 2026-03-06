from __future__ import annotations

import re


SECTION_TITLE_PATTERNS = [
    r"INDICATIONS AND USAGE",
    r"DOSAGE AND ADMINISTRATION",
    r"DOSAGE FORMS AND STRENGTHS",
    r"CONTRAINDICATIONS",
    r"WARNINGS AND PRECAUTIONS",
    r"ADVERSE REACTIONS",
    r"DRUG INTERACTIONS",
    r"USE IN SPECIFIC POPULATIONS",
    r"OVERDOSAGE",
    r"DESCRIPTION",
    r"CLINICAL PHARMACOLOGY",
    r"NONCLINICAL TOXICOLOGY",
    r"CLINICAL STUDIES",
    r"HOW SUPPLIED/STORAGE AND HANDLING",
    r"PATIENT COUNSELING INFORMATION",
]


def normalize_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def split_lines(text: str) -> list[str]:
    lines = [normalize_whitespace(line) for line in text.splitlines()]
    return [line for line in lines if line]


def looks_like_section_title(line: str) -> bool:
    """
    FDA SPL 원문에서 대표 section title처럼 보이는지 판정.
    너무 공격적으로 잡지 않도록 보수적으로 판단.
    """
    if not line:
        return False

    upper = line.strip().upper()

    # 너무 긴 줄은 제목일 확률 낮음
    if len(upper) > 80:
        return False

    # 알파벳/숫자/기호 외 문자가 너무 많으면 제외
    allowed_ratio = sum(ch.isupper() or ch.isdigit() or ch in " -/(),.&" for ch in upper) / max(len(upper), 1)
    if allowed_ratio < 0.85:
        return False

    # 대표 패턴 우선 허용
    for pattern in SECTION_TITLE_PATTERNS:
        if re.fullmatch(pattern, upper):
            return True

    # 번호 섹션도 일부 허용: "17 PATIENT COUNSELING INFORMATION"
    if re.fullmatch(r"\d{1,2}\s+[A-Z][A-Z0-9 /(),.&-]+", upper):
        return True

    # 전부 대문자인 짧은 라인 허용
    if upper == line.strip() and upper.isupper() and 3 <= len(upper) <= 80:
        return True

    return False


def extract_sections_from_text(full_text: str) -> list[dict]:
    """
    전체 텍스트를 line 기반으로 section으로 분리.
    section이 하나도 없으면 전체를 하나의 section으로 반환.
    """
    lines = split_lines(full_text)

    sections: list[dict] = []
    current_title = "전체 문서"
    current_lines: list[str] = []

    for line in lines:
        if looks_like_section_title(line):
            # 이전 section 저장
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    sections.append(
                        {
                            "section_title": current_title,
                            "section_text": body,
                        }
                    )
            current_title = line.strip()
            current_lines = []
        else:
            current_lines.append(line)

    # 마지막 section 저장
    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            sections.append(
                {
                    "section_title": current_title,
                    "section_text": body,
                }
            )

    # 섹션이 전혀 안 잡히면 전체 문서 하나로 반환
    if not sections:
        normalized = "\n".join(lines).strip()
        if normalized:
            sections = [
                {
                    "section_title": "전체 문서",
                    "section_text": normalized,
                }
            ]

    # 빈 section 제거
    cleaned_sections = []
    for sec in sections:
        sec_text = sec["section_text"].strip()
        if sec_text:
            cleaned_sections.append(
                {
                    "section_title": sec["section_title"].strip(),
                    "section_text": sec_text,
                    "char_length": len(sec_text),
                }
            )

    return cleaned_sections