import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import chardet

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_TEXT_LENGTH = 100_000
EXTRACT_TIMEOUT = 5.0
CHARDET_SAMPLE_SIZE = 10 * 1024
DEFAULT_ENCODINGS = ["utf-8", "utf-16", "gbk", "gb2312", "latin-1"]

EXTENSIONS_TXT = {".txt", ".md", ".log", ".csv"}
EXTENSIONS_PDF = {".pdf"}
EXTENSIONS_DOCX = {".docx"}
EXTENSIONS_XLSX = {".xlsx"}

def extract_text(path: Path, file_ext: str) -> str:
    ext = f".{file_ext.lstrip('.').lower()}"
    if ext in EXTENSIONS_TXT:
        return _run_with_timeout(extract_txt, path)
    if ext in EXTENSIONS_PDF:
        return _run_with_timeout(extract_pdf, path)
    if ext in EXTENSIONS_DOCX:
        return _run_with_timeout(extract_docx, path)
    if ext in EXTENSIONS_XLSX:
        return _run_with_timeout(extract_xlsx, path)
    return ""

def _run_with_timeout(fn, path: Path, timeout: float = EXTRACT_TIMEOUT):
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn, path)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            logger.warning("Extraction timed out: %s", path)
            return ""
        except Exception:
            logger.exception("Extraction failed: %s", path)
            return ""

def extract_txt(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_FILE_SIZE:
            return ""
        sample = _read_sample(path)
        encoding = _detect_encoding(sample)
        try:
            text = path.read_text(encoding=encoding, errors="replace")
        except (LookupError, UnicodeDecodeError):
            for enc in DEFAULT_ENCODINGS:
                try:
                    text = path.read_text(encoding=enc, errors="replace")
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            else:
                return ""
        return text[:MAX_TEXT_LENGTH]
    except Exception:
        logger.exception("TXT extraction failed: %s", path)
        return ""

def _read_sample(path: Path) -> bytes:
    with path.open("rb") as f:
        return f.read(CHARDET_SAMPLE_SIZE)

def _detect_encoding(sample: bytes) -> str:
    result = chardet.detect(sample)
    return result.get("encoding", "utf-8") or "utf-8"

def extract_pdf(path: Path) -> str:
    import fitz
    try:
        if path.stat().st_size > MAX_FILE_SIZE:
            return ""
        text_pages = []
        try:
            doc = fitz.open(str(path))
            for page in doc:
                text_pages.append(page.get_text())
            doc.close()
        except Exception:
            logger.exception("PDF extraction failed: %s", path)
            return ""
        full = " ".join(text_pages)
        if len(full.strip()) < 50:
            return ""
        return full[:MAX_TEXT_LENGTH]
    except Exception:
        logger.exception("PDF extraction failed: %s", path)
        return ""

def extract_docx(path: Path) -> str:
    from docx import Document
    if path.stat().st_size > MAX_FILE_SIZE:
        return ""
    try:
        doc = Document(str(path))
        parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    parts.append(cell.text)
        return " ".join(parts)[:MAX_TEXT_LENGTH]
    except Exception:
        logger.exception("DOCX extraction failed: %s", path)
        return ""

def extract_xlsx(path: Path) -> str:
    from openpyxl import load_workbook
    if path.stat().st_size > MAX_FILE_SIZE:
        return ""
    try:
        wb = load_workbook(str(path), read_only=True, data_only=True)
        parts = []
        for sheet in wb.worksheets:
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.value is not None:
                        parts.append(str(cell.value))
        wb.close()
        return " ".join(parts)[:MAX_TEXT_LENGTH]
    except Exception:
        logger.exception("XLSX extraction failed: %s", path)
        return ""
