import streamlit as st
from pathlib import Path

from src.utils import ensure_file_exists
from src.zip_loader import (
    build_inner_zip_index,
    read_xml_from_inner_zip,
)
from src.spl_parser import parse_spl_xml


st.set_page_config(
    page_title="FDA SPL RAG 데모",
    page_icon="🧪",
    layout="wide",
)

st.title("🧪 FDA SPL 기반 한국어 RAG 데모")
st.caption("Iteration 1 빠른 수정판 - 바깥 ZIP → 일부 내부 ZIP → XML 파싱")

with st.sidebar:
    st.header("설정")
    default_path = "data/dm_spl_release_human_rx_part1.zip"
    zip_path = st.text_input("바깥 ZIP 파일 경로", value=default_path)
    show_full_text = st.checkbox("전체 텍스트 표시", value=False)
    scan_limit = st.number_input(
        "초기 스캔할 내부 ZIP 개수",
        min_value=1,
        max_value=5000,
        value=10,
        step=1,
        help="처음에는 일부만 빠르게 스캔합니다.",
    )

st.markdown("## 파이프라인 단계")

col1, col2, col3 = st.columns(3)

with col1:
    st.info("1단계\n\n바깥 ZIP 파일 확인")

with col2:
    st.info("2단계\n\n일부 내부 ZIP 탐색 및 XML 포함 여부 확인")

with col3:
    st.info("3단계\n\n선택한 내부 ZIP의 XML 파싱 및 미리보기")

st.divider()

try:
    file_path = ensure_file_exists(zip_path)
    st.success(f"ZIP 파일 확인 완료: `{file_path}`")
except Exception as e:
    st.error(str(e))
    st.stop()

with st.spinner("내부 ZIP 일부를 빠르게 스캔하는 중입니다..."):
    try:
        total_inner_count, indexed_inner_zips = build_inner_zip_index(
            str(file_path),
            limit=int(scan_limit),
        )
    except Exception as e:
        st.error(f"내부 ZIP 인덱스 생성 실패: {e}")
        st.stop()

valid_entries = [row for row in indexed_inner_zips if row.get("xml_count", 0) > 0]

left, right = st.columns([1, 2])

with left:
    st.subheader("📦 ZIP 구조 정보")
    st.write(f"바깥 ZIP 파일명: `{Path(zip_path).name}`")
    st.write(f"전체 내부 ZIP 개수: `{total_inner_count}`")
    st.write(f"현재 스캔한 내부 ZIP 수: `{len(indexed_inner_zips)}`")
    st.write(f"현재 스캔 범위 내 XML 포함 내부 ZIP 수: `{len(valid_entries)}`")

    if not indexed_inner_zips:
        st.warning("스캔된 내부 ZIP이 없습니다.")
        st.stop()

    with st.expander("스캔 결과 미리보기"):
        for row in indexed_inner_zips[:50]:
            st.write(
                {
                    "inner_zip_name": row["inner_zip_name"],
                    "xml_count": row.get("xml_count", 0),
                    "error": row.get("error", ""),
                }
            )

    if not valid_entries:
        st.warning("현재 스캔 범위 안에서 XML이 포함된 내부 ZIP을 찾지 못했습니다.")
        st.info("scan_limit를 30, 50, 100처럼 조금씩 올려보세요.")
        st.stop()

    option_map = {
        f"{idx + 1}. {Path(row['inner_zip_name']).name} (XML {row['xml_count']}개)": row
        for idx, row in enumerate(valid_entries)
    }

    selected_label = st.selectbox(
        "확인할 내부 ZIP 선택",
        options=list(option_map.keys()),
    )

    selected_entry = option_map[selected_label]
    selected_inner_zip_name = selected_entry["inner_zip_name"]
    selected_xml_name = selected_entry["xml_files"][0]

    st.write("선택한 내부 ZIP:")
    st.code(selected_inner_zip_name, language="text")

    st.write("선택된 XML:")
    st.code(selected_xml_name, language="text")

with right:
    st.subheader("🔍 XML 파싱 결과")

    try:
        xml_text = read_xml_from_inner_zip(
            str(file_path),
            selected_inner_zip_name,
            selected_xml_name,
        )
        parsed = parse_spl_xml(xml_text)
    except Exception as e:
        st.error(f"XML 파싱 실패: {e}")
        st.stop()

    meta_col1, meta_col2 = st.columns(2)

    with meta_col1:
        st.metric("문서 제목", parsed["title"])
        st.metric("문서 ID", parsed["document_id"])

    with meta_col2:
        st.metric("코드 표시명", parsed["code_display"])
        st.metric("추출 텍스트 길이", f'{parsed["text_length"]:,} 글자')

    st.markdown("### 텍스트 미리보기")
    st.text_area(
        "파싱된 문서 내용 일부",
        value=parsed["preview"],
        height=400,
    )

    if show_full_text:
        st.markdown("### 전체 텍스트")
        st.text_area(
            "전체 문서 텍스트",
            value=parsed["full_text"],
            height=600,
        )

st.divider()

with st.expander("현재 Iteration에서 검증해야 할 것"):
    st.markdown(
        """
        - 바깥 ZIP이 정상적으로 읽히는지
        - 전체 내부 ZIP 개수가 보이는지
        - 현재 스캔 범위 내 XML 포함 내부 ZIP이 표시되는지
        - 내부 ZIP 선택이 가능한지
        - 선택한 XML의 제목/ID/텍스트가 보이는지
        """
    )