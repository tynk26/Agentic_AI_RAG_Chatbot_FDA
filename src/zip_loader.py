from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile


def list_inner_zip_entries(outer_zip_path: str) -> list[str]:
    """
    바깥 ZIP 안에 들어있는 내부 ZIP 파일 목록을 반환한다.
    예: prescription/20060131_xxx.zip
    """
    path = Path(outer_zip_path)
    with ZipFile(path, "r") as outer_zip:
        inner_zips = [
            name
            for name in outer_zip.namelist()
            if name.lower().endswith(".zip")
        ]
    return sorted(inner_zips)


def list_xml_files_in_inner_zip(outer_zip_path: str, inner_zip_name: str) -> list[str]:
    """
    바깥 ZIP 안의 특정 내부 ZIP을 열고, 그 안의 XML 파일 목록을 반환한다.
    """
    path = Path(outer_zip_path)

    with ZipFile(path, "r") as outer_zip:
        inner_zip_bytes = outer_zip.read(inner_zip_name)

    with ZipFile(BytesIO(inner_zip_bytes), "r") as inner_zip:
        xml_files = [
            name
            for name in inner_zip.namelist()
            if name.lower().endswith(".xml")
        ]

    return sorted(xml_files)


def build_inner_zip_index(outer_zip_path: str, limit: int | None = None) -> tuple[int, list[dict]]:
    """
    UI 표시용 인덱스를 만든다.

    반환:
    (
      전체 내부 ZIP 개수,
      [
        {
          "inner_zip_name": "...",
          "xml_count": 1,
          "xml_files": ["abc.xml"]
        }
      ]
    )
    """
    inner_zips = list_inner_zip_entries(outer_zip_path)
    total_inner_zip_count = len(inner_zips)

    if limit is not None:
        inner_zips = inner_zips[:limit]

    results: list[dict] = []

    for inner_zip_name in inner_zips:
        try:
            xml_files = list_xml_files_in_inner_zip(outer_zip_path, inner_zip_name)
            results.append(
                {
                    "inner_zip_name": inner_zip_name,
                    "xml_count": len(xml_files),
                    "xml_files": xml_files,
                }
            )
        except Exception as e:
            results.append(
                {
                    "inner_zip_name": inner_zip_name,
                    "xml_count": 0,
                    "xml_files": [],
                    "error": str(e),
                }
            )

    return total_inner_zip_count, results


def read_xml_from_inner_zip(
    outer_zip_path: str,
    inner_zip_name: str,
    xml_name: str,
) -> str:
    """
    바깥 ZIP -> 내부 ZIP -> XML 파일을 순서대로 열어 XML 텍스트를 반환한다.
    """
    path = Path(outer_zip_path)

    with ZipFile(path, "r") as outer_zip:
        inner_zip_bytes = outer_zip.read(inner_zip_name)

    with ZipFile(BytesIO(inner_zip_bytes), "r") as inner_zip:
        with inner_zip.open(xml_name) as f:
            return f.read().decode("utf-8", errors="ignore")