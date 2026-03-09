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
from src.retriever import build_tfidf_index, search_tfidf, highlight_text, expand_query


st.set_page_config(
    page_title="FDA SPL RAG 데모",
    page_icon="🧪",
    layout="wide",
)

st.title("🧪 FDA SPL 기반 한국어 RAG 데모")
st.caption("Iteration 4 - 검색 품질 개선판: 청킹 개선 + 질의 확장 + 점수 해석 강화")

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
        value=900,
        step=100,
    )

    chunk_overlap = st.number_input(
        "청크 오버랩(문자 수)",
        min_value=0,
        max_value=1000,
        value=120,
        step=20,
    )

    top_k = st.number_input(
        "검색 결과 개수",
        min_value=1,
        max_value=10,
        value=5,
        step=1,
    )

    show_full_section = st.checkbox("선택한 섹션 원문 전체 표시", value=False)
    show_chunk_text = st.checkbox("선택한 검색 청크 원문 표시", value=True)
    show_highlighted = st.checkbox("검색어 하이라이트 표시", value=True)

st.markdown("## 파이프라인 단계")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.info("1단계\n\n샘플 XML 문서 수집")

with col2:
    st.info("2단계\n\n문서 파싱")

with col3:
    st.info("3단계\n\nFDA SPL 섹션 추출")

with col4:
    st.info("4단계\n\n경계 기반 청크 생성")

with col5:
    st.info("5단계\n\n질의 확장 TF-IDF 검색")

st.divider()

try:
    file_path = ensure_file_exists(zip_path)
    st.success(f"ZIP 파일 확인 완료: `{file_path}`")
except Exception as e:
    st.error(str(e))
    st.stop()


@st.cache_data(show_spinner=False)
def load_sample_documents(
    zip_path_str: str,
    sample_size_value: int,
    chunk_size_value: int,
    chunk_overlap_value: int,
) -> list[dict]:
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
                chunk_size=chunk_size_value,
                overlap=chunk_overlap_value,
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


@st.cache_resource(show_spinner=False)
def build_cached_index(all_chunks: list[dict]) -> dict:
    return build_tfidf_index(all_chunks)


with st.spinner("샘플 문서를 파싱하고 섹션/청크를 생성하는 중입니다..."):
    documents = load_sample_documents(
        str(file_path),
        int(sample_size),
        int(chunk_size),
        int(chunk_overlap),
    )

valid_documents = [doc for doc in documents if not doc["error"]]

if not documents:
    st.error("샘플 문서를 불러오지 못했습니다.")
    st.stop()

all_chunks: list[dict] = []
for doc in valid_documents:
    all_chunks.extend(doc["chunks"])

if not all_chunks:
    st.error("인덱싱할 청크가 없습니다.")
    st.stop()

with st.spinner("TF-IDF 인덱스를 생성하는 중입니다..."):
    index_bundle = build_cached_index(all_chunks)

summary_col1, summary_col2, summary_col3, summary_col4, summary_col5 = st.columns(5)

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

with summary_col5:
    st.metric("인덱싱된 청크 수", index_bundle["corpus_size"])

st.divider()

st.subheader("🔎 질문으로 청크 검색")

default_query = "aspirin interactions"
user_query = st.text_input(
    "질문 입력",
    value=default_query,
    help="예: aspirin interactions, side effects, warnings, contraindications",
)

expanded_query = expand_query(user_query)

query_col1, query_col2 = st.columns([1.6, 1.0])

with query_col1:
    st.markdown("### 확장된 검색 질의")
    st.code(expanded_query, language="text")

with query_col2:
    st.markdown("### 점수 해석")
    st.write("- raw_score: TF-IDF 원시 유사도")
    st.write("- relative_score: 이번 검색 결과 내 최고점 대비 상대점수")

search_button = st.button("검색 실행", type="primary")

search_results: list[dict] = []
if search_button or user_query.strip():
    search_results = search_tfidf(
        query=user_query,
        index_bundle=index_bundle,
        top_k=int(top_k),
    )

result_col1, result_col2 = st.columns([1.15, 1.85])

with result_col1:
    st.subheader("📋 검색 결과 목록")

    if not search_results:
        st.warning("검색 결과가 없습니다.")
        st.stop()

    result_rows = []
    for row in search_results:
        result_rows.append(
            {
                "rank": row["rank"],
                "raw_score": row["raw_score"],
                "relative_score": row["relative_score"],
                "document_title": row["document_title"][:45],
                "section_title": row["section_title"][:35],
                "chunk_index": row["chunk_index"],
                "chunk_length": row["chunk_length"],
            }
        )

    st.dataframe(pd.DataFrame(result_rows), use_container_width=True)

    result_option_map = {}
    for row in search_results:
        label = (
            f"{row['rank']}위 | 상대 {row['relative_score']:.1f} | "
            f"{row['section_title'][:25]} | 청크 {row['chunk_index']}"
        )
        result_option_map[label] = row

    selected_result_label = st.selectbox(
        "상세 확인할 검색 결과 선택",
        options=list(result_option_map.keys()),
    )
    selected_result = result_option_map[selected_result_label]

    st.write("선택한 검색 결과 메타데이터")
    st.json(
        {
            "rank": selected_result["rank"],
            "raw_score": selected_result["raw_score"],
            "relative_score": selected_result["relative_score"],
            "document_title": selected_result["document_title"],
            "section_title": selected_result["section_title"],
            "chunk_index": selected_result["chunk_index"],
            "chunk_length": selected_result["chunk_length"],
            "inner_zip_name": selected_result["inner_zip_name"],
            "xml_name": selected_result["xml_name"],
        }
    )

with result_col2:
    st.subheader("📌 근거 청크 상세")

    matched_document = None
    for doc in valid_documents:
        if (
            doc["title"] == selected_result["document_title"]
            and doc["xml_name"] == selected_result["xml_name"]
        ):
            matched_document = doc
            break

    if matched_document is None:
        st.error("선택한 결과에 대응하는 원본 문서를 찾지 못했습니다.")
        st.stop()

    matched_section = None
    for sec in matched_document["sections"]:
        if sec["section_title"] == selected_result["section_title"]:
            matched_section = sec
            break

    if matched_section is None:
        st.warning("대응 섹션을 찾지 못했습니다.")
    else:
        st.markdown("### 검색된 섹션 정보")
        st.json(
            {
                "document_title": matched_document["title"],
                "section_title": matched_section["section_title"],
                "section_char_length": matched_section["char_length"],
            }
        )

        section_preview = matched_section["section_text"]
        if not show_full_section:
            section_preview = section_preview[:3000]

        if show_highlighted:
            highlighted_section = highlight_text(section_preview, user_query)
            st.markdown("### 섹션 원문 (하이라이트)")
            st.markdown(
                f"""
                <div style="padding:12px;border:1px solid #444;border-radius:8px;max-height:260px;overflow:auto;">
                {highlighted_section}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.text_area(
                "섹션 원문",
                value=section_preview,
                height=240,
            )

    if show_chunk_text:
        st.markdown("### 검색된 청크 원문")

        if show_highlighted:
            st.markdown(
                f"""
                <div style="padding:12px;border:1px solid #444;border-radius:8px;max-height:320px;overflow:auto;">
                {selected_result["highlighted_chunk_text"]}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.text_area(
                "청크 원문",
                value=selected_result["chunk_text"],
                height=320,
            )

st.divider()

left_debug, right_debug = st.columns([1.1, 1.3])

with left_debug:
    st.subheader("📄 샘플 문서 요약")

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

with right_debug:
    st.subheader("🧪 검색 디버그 요약")
    st.json(
        {
            "query": user_query,
            "expanded_query": expanded_query,
            "top_k": int(top_k),
            "sample_size": int(sample_size),
            "chunk_size": int(chunk_size),
            "chunk_overlap": int(chunk_overlap),
            "indexed_chunks": index_bundle["corpus_size"],
        }
    )

with st.expander("이번 Iteration에서 검증해야 할 것"):
    st.markdown(
        """
        - 단어가 이전보다 덜 잘리는지
        - 확장된 검색 질의가 보이는지
        - raw_score와 relative_score가 같이 보이는지
        - interactions / side effects / warnings 질의에서 더 자연스럽게 검색되는지
        - 검색어 하이라이트가 청크에 적용되는지
        """
    )

with st.expander("질문 예시"):
    st.markdown(
        """
        - aspirin interactions
        - warfarin interactions
        - side effects
        - warnings
        - contraindications
        - dosage
        - pregnancy
        """
    )

with st.expander("다음 Iteration 예고"):
    st.markdown(
        """
        - 검색된 상위 청크를 바탕으로 답변 초안 생성
        - 질문 + 근거 청크 조합으로 간단한 RAG 응답 생성기 구현
        - 프론트에서 질문 → 검색 → 답변 → 근거를 한 번에 확인
        """
    )