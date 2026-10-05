"""Local PDF/TXT resume extraction and safe upload persistence."""
from pathlib import Path
import re
from uuid import uuid4
from pypdf import PdfReader


def load_resume(path: str | Path) -> str:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError("Resume file does not exist")
    if path.suffix.lower() == ".txt":
        text = path.read_text(encoding="utf-8")
    elif path.suffix.lower() == ".pdf":
        try:
            reader = PdfReader(path)
            if reader.is_encrypted:
                raise ValueError("Encrypted resumes are not supported")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise ValueError("Could not extract PDF resume text") from exc
    else:
        raise ValueError("Resume must be PDF or TXT")
    text = "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        raise ValueError("Resume contains no extractable text; scanned PDFs need OCR outside this phase")
    return text


def save_resume_upload(data: bytes, filename: str, directory: Path) -> Path:
    suffix = Path(filename).suffix.lower()
    if suffix not in (".pdf", ".txt"):
        raise ValueError("Resume must be PDF or TXT")
    if not data or len(data) > 10 * 1024 * 1024:
        raise ValueError("Resume must be between 1 byte and 10 MB")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"resume_{uuid4().hex}{suffix}"
    path.write_bytes(data)
    try:
        load_resume(path)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path
