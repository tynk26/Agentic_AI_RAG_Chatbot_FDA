from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile


def list_inner_zip_entries(outer_zip_path: str) -> list[str]:
    path = Path(outer_zip_path)
    with ZipFile(path, "r") as outer_zip:
        inner_zips = [
            name
            for name in outer_zip.namelist()
            if name.lower().endswith(".zip")
        ]
    return sorted(inner_zips)


def list_xml_files_in_inner_zip(outer_zip_path: str, inner_zip_name: str) -> list[str]:
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
    path = Path(outer_zip_path)

    with ZipFile(path, "r") as outer_zip:
        inner_zip_bytes = outer_zip.read(inner_zip_name)

    with ZipFile(BytesIO(inner_zip_bytes), "r") as inner_zip:
        with inner_zip.open(xml_name) as f:
            return f.read().decode("utf-8", errors="ignore")


def get_sample_xml_entries(outer_zip_path: str, sample_size: int = 10) -> list[dict]:
    """
    XML이 포함된 내부 ZIP 중 앞에서부터 sample_size개를 반환.
    """
    _, indexed_inner_zips = build_inner_zip_index(outer_zip_path, limit=sample_size * 5)

    valid_entries = []
    for row in indexed_inner_zips:
        if row.get("xml_count", 0) > 0:
            valid_entries.append(
                {
                    "inner_zip_name": row["inner_zip_name"],
                    "xml_name": row["xml_files"][0],
                }
            )
        if len(valid_entries) >= sample_size:
            break

    return valid_entries