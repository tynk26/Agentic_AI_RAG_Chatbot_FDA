import streamlit as st
from pathlib import Path
import pandas as pd

from src.utils import ensure_file_exists
from src.zip_loader import (
    get_sample_xml_entries,
    read_xml_from_inner_zip,
)
from src.spl_parser import parse_spl_xml
from src.section_extractor import extract_sections_from_text
from src.chunker import build_chunk_records


st.set_page_config(
    page_title="FDA SPL RAG 데모",
    page_icon="🧪",
    layout="wide",
)

st.title("🧪 FDA SPL 기반 한국어 RAG 데모")
st.caption("Iteration 2 - 샘플 문서 → 섹션 추출 → 청크 생성")

with st.sidebar:
    st.header("설정")
    default_path = "data/dm_spl_release_human_rx_part1.zip"
    zip_path = st.text_input("바깥 ZIP 파일 경로", value=default_path)

    sample_size = st.number_input(
        "샘플 문서 수",
        min_value=1,
        max_value=20,
        value=10,
        step=1,
    )

    chunk_size = st.number_input(
        "청크 크기(문자 수)",
        min_value=200,
        max_value=3000,
        value=800,
        step=100,
    )

    chunk_overlap = st.number_input(
        "청크 오버랩(문자 수)",
        min_value=0,
        max_value=1000,
        value=150,
        step=50,
    )

    show_full_section = st.checkbox("선택한 섹션 원문 전체 표시", value=False)
    show_chunk_text = st.checkbox("선택한 청크 원문 표시", value=True)

st.markdown("## 파이프라인 단계")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.info("1단계\n\n샘플 XML 문서 수집")

with col2:
    st.info("2단계\n\n문서 파싱")

with col3:
    st.info("3단계\n\nFDA SPL 섹션 추출")

with col4:
    st.info("4단계\n\n섹션별 청크 생성")

st.divider()

try:
    file_path = ensure_file_exists(zip_path)
    st.success(f"ZIP 파일 확인 완료: `{file_path}`")
except Exception as e:
    st.error(str(e))
    st.stop()


@st.cache_data(show_spinner=False)
def load_sample_documents(zip_path_str: str, sample_size_value: int) -> list[dict]:
    sample_entries = get_sample_xml_entries(zip_path_str, sample_size=sample_size_value)

    documents: list[dict] = []

    for entry in sample_entries:
        inner_zip_name = entry["inner_zip_name"]
        xml_name = entry["xml_name"]

        try:
            xml_text = read_xml_from_inner_zip(zip_path_str, inner_zip_name, xml_name)
            parsed = parse_spl_xml(xml_text)
            sections = extract_sections_from_text(parsed["full_text"])

            chunk_records = build_chunk_records(
                inner_zip_name=inner_zip_name,
                xml_name=xml_name,
                document_title=parsed["title"],
                sections=sections,
                chunk_size=int(chunk_size_value),
                overlap=int(chunk_overlap_value),
            )
        except Exception as ex:
            documents.append(
                {
                    "inner_zip_name": inner_zip_name,
                    "xml_name": xml_name,
                    "title": "파싱 실패",
                    "document_id": "",
                    "code_display": "",
                    "full_text": "",
                    "sections": [],
                    "chunks": [],
                    "error": str(ex),
                }
            )
            continue

        documents.append(
            {
                "inner_zip_name": inner_zip_name,
                "xml_name": xml_name,
                "title": parsed["title"],
                "document_id": parsed["document_id"],
                "code_display": parsed["code_display"],
                "full_text": parsed["full_text"],
                "sections": sections,
                "chunks": chunk_records,
                "error": "",
            }
        )

    return documents


chunk_size_value = int(chunk_size)
chunk_overlap_value = int(chunk_overlap)

with st.spinner("샘플 문서를 파싱하고 섹션/청크를 생성하는 중입니다..."):
    documents = load_sample_documents(str(file_path), int(sample_size))

valid_documents = [doc for doc in documents if not doc["error"]]

if not documents:
    st.error("샘플 문서를 불러오지 못했습니다.")
    st.stop()

summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

with summary_col1:
    st.metric("샘플 문서 수", len(documents))

with summary_col2:
    st.metric("정상 파싱 문서 수", len(valid_documents))

with summary_col3:
    total_sections = sum(len(doc["sections"]) for doc in valid_documents)
    st.metric("총 추출 섹션 수", total_sections)

with summary_col4:
    total_chunks = sum(len(doc["chunks"]) for doc in valid_documents)
    st.metric("총 생성 청크 수", total_chunks)

st.divider()

left, middle, right = st.columns([1.1, 1.1, 1.8])

with left:
    st.subheader("📄 샘플 문서 목록")

    document_options = {}
    for idx, doc in enumerate(documents):
        label = f"{idx + 1}. {Path(doc['inner_zip_name']).name} | {doc['title'][:40]}"
        document_options[label] = doc

    selected_document_label = st.selectbox(
        "문서 선택",
        options=list(document_options.keys()),
    )
    selected_document = document_options[selected_document_label]

    st.write("선택한 내부 ZIP")
    st.code(selected_document["inner_zip_name"], language="text")

    st.write("선택한 XML")
    st.code(selected_document["xml_name"], language="text")

    if selected_document["error"]:
        st.error(f"이 문서는 파싱 실패: {selected_document['error']}")
        st.stop()

    st.write("문서 메타데이터")
    st.json(
        {
            "title": selected_document["title"],
            "document_id": selected_document["document_id"],
            "code_display": selected_document["code_display"],
            "section_count": len(selected_document["sections"]),
            "chunk_count": len(selected_document["chunks"]),
        }
    )

    with st.expander("전체 샘플 문서 요약표"):
        rows = []
        for doc in documents:
            rows.append(
                {
                    "inner_zip_name": Path(doc["inner_zip_name"]).name,
                    "title": doc["title"],
                    "section_count": len(doc["sections"]),
                    "chunk_count": len(doc["chunks"]),
                    "error": doc["error"],
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

with middle:
    st.subheader("🧩 섹션 목록")

    sections = selected_document["sections"]

    if not sections:
        st.warning("추출된 섹션이 없습니다.")
        st.stop()

    section_options = {}
    for idx, sec in enumerate(sections):
        label = f"{idx + 1}. {sec['section_title']} ({sec['char_length']}자)"
        section_options[label] = sec

    selected_section_label = st.selectbox(
        "섹션 선택",
        options=list(section_options.keys()),
    )
    selected_section = section_options[selected_section_label]

    st.write("선택한 섹션 메타데이터")
    st.json(
        {
            "section_title": selected_section["section_title"],
            "char_length": selected_section["char_length"],
        }
    )

    preview_text = selected_section["section_text"]
    if not show_full_section:
        preview_text = preview_text[:3000]

    st.text_area(
        "섹션 원문",
        value=preview_text,
        height=500,
    )

with right:
    st.subheader("🧱 청크 목록")

    section_chunks = [
        chunk
        for chunk in selected_document["chunks"]
        if chunk["section_title"] == selected_section["section_title"]
    ]

    if not section_chunks:
        st.warning("이 섹션에서는 생성된 청크가 없습니다.")
        st.stop()

    chunk_options = {}
    for chunk in section_chunks:
        label = f"청크 {chunk['chunk_index']} | {chunk['chunk_length']}자"
        chunk_options[label] = chunk

    selected_chunk_label = st.selectbox(
        "청크 선택",
        options=list(chunk_options.keys()),
    )
    selected_chunk = chunk_options[selected_chunk_label]

    st.write("선택한 청크 메타데이터")
    st.json(
        {
            "document_title": selected_chunk["document_title"],
            "section_title": selected_chunk["section_title"],
            "chunk_index": selected_chunk["chunk_index"],
            "chunk_length": selected_chunk["chunk_length"],
            "xml_name": selected_chunk["xml_name"],
        }
    )

    chunk_table_rows = []
    for chunk in section_chunks:
        chunk_table_rows.append(
            {
                "chunk_index": chunk["chunk_index"],
                "chunk_length": chunk["chunk_length"],
                "section_title": chunk["section_title"],
            }
        )

    st.dataframe(pd.DataFrame(chunk_table_rows), use_container_width=True)

    if show_chunk_text:
        st.text_area(
            "청크 원문",
            value=selected_chunk["chunk_text"],
            height=400,
        )

st.divider()

with st.expander("이번 Iteration에서 검증해야 할 것"):
    st.markdown(
        """
        - 샘플 문서 10개가 로드되는지
        - 각 문서에서 section이 추출되는지
        - section 선택 시 원문이 보이는지
        - section별 chunk가 생성되는지
        - chunk 길이와 인덱스가 표시되는지
        """
    )

with st.expander("다음 Iteration 예고"):
    st.markdown(
        """
        - 샘플 청크 전체를 인덱스로 묶기
        - TF-IDF 기반 검색
        - 사용자 질의 입력
        - 어떤 chunk가 검색되었는지 프론트에서 확인
        """
    )