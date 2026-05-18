import io
import pdfplumber
from docx import Document


def parse_resume(file_bytes: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        return _parse_pdf(file_bytes)
    if name.endswith(".docx"):
        return _parse_docx(file_bytes)
    raise ValueError(f"Unsupported file type: {filename}")


def _parse_pdf(file_bytes: bytes) -> str:
    try:
        parts = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    parts.append(text)
        if not parts:
            raise ValueError("No extractable text found — try a text-based PDF")
        return "\n".join(parts)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Could not read PDF: {e}") from e


def _parse_docx(file_bytes: bytes) -> str:
    try:
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        raise ValueError(f"Could not read DOCX: {e}") from e
