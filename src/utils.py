from pathlib import Path


def ensure_file_exists(file_path: str) -> Path:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
    if not path.is_file():
        raise ValueError(f"파일 경로가 아닙니다: {file_path}")
    return path


def safe_text(text: str | None) -> str:
    if text is None:
        return ""
    return " ".join(text.split())