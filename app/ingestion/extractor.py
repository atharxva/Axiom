import io, re
from pypdf import PdfReader

def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Extract and sanitize text from PDF or plain text files."""
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))
        pages_text = [page.extract_text() or "" for page in reader.pages]
        raw_text = "\n\n".join(pages_text)
    else:
        raw_text = file_bytes.decode("utf-8", errors="ignore")

    # 1. Strip web headers/footers (e.g. URLs, date stamps, page counts like "5/16")
    clean = re.sub(r"https?://\S+", "", raw_text)
    clean = re.sub(r"\d{1,2}/\d{1,2}/\d{4},\s*\d{1,2}:\d{2}\s*Supplier Code of Conduct.*", "", clean)
    clean = re.sub(r"\b\d+\s*/\s*\d+\b", "", clean)

    # 2. Fix broken hyphenated words at line wraps (e.g., "oper-\nations" -> "operations")
    clean = re.sub(r"(\w+)-\n+(\w+)", r"\1\2", clean)

    # 3. Collapse excessive empty newlines
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean.strip()
