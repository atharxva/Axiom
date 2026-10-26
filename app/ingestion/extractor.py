import io, re
from pypdf import PdfReader

def extract_pages_from_file(file_bytes: bytes, filename: str) -> list[tuple[int, str]]:
    """Extract list of (page_number, text) tuples from PDF or plain text files."""
    pages: list[tuple[int, str]] = []
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))
        for idx, page in enumerate(reader.pages, start=1):
            txt = page.extract_text() or ""
            pages.append((idx, _clean_text(txt)))
    else:
        raw_text = file_bytes.decode("utf-8", errors="ignore")
        pages.append((1, _clean_text(raw_text)))
    return pages

def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Extract and sanitize text from PDF or plain text files."""
    pages = extract_pages_from_file(file_bytes, filename)
    return "\n\n".join(txt for _, txt in pages if txt.strip())

def _clean_text(raw_text: str) -> str:
    clean = re.sub(r"https?://\S+", "", raw_text)
    clean = re.sub(r"\d{1,2}/\d{1,2}/\d{4},\s*\d{1,2}:\d{2}\s*Supplier Code of Conduct.*", "", clean)
    clean = re.sub(r"\b\d+\s*/\s*\d+\b", "", clean)
    clean = re.sub(r"(\w+)-\n+(\w+)", r"\1\2", clean)
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean.strip()

