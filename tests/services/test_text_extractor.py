import pytest
from pathlib import Path
from src.app.services.text_extractor import (
    extract_text, extract_txt, extract_pdf, extract_docx, extract_xlsx,
    MAX_FILE_SIZE, MAX_TEXT_LENGTH,
)

class TestTextExtractor:
    def test_extract_txt_utf8(self, tmp_path):
        p = tmp_path / "test.txt"
        p.write_text("hello world", encoding="utf-8")
        assert extract_text(p, "txt") == "hello world"

    def test_extract_txt_gbk(self, tmp_path):
        p = tmp_path / "test.txt"
        p.write_text("中文测试", encoding="gbk")
        assert extract_text(p, "txt") == "中文测试"

    def test_extract_txt_unknown_encoding_falls_back(self, tmp_path):
        p = tmp_path / "test.txt"
        raw = b"\xff\xfe\x68\x00\x65\x00\x6c\x00\x6c\x00\x6f\x00"
        p.write_bytes(raw)
        result = extract_text(p, "txt")
        assert len(result) > 0

    def test_extract_pdf_text(self, tmp_path):
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "PDF content test for FTS indexing. This is a longer sentence to ensure we exceed the fifty character scan detection threshold.")
        pdf_path = tmp_path / "test.pdf"
        doc.save(str(pdf_path))
        doc.close()
        result = extract_text(pdf_path, "pdf")
        assert "PDF content test" in result

    def test_extract_pdf_scan_detected(self, tmp_path):
        import fitz
        doc = fitz.open()
        doc.new_page()
        pdf_path = tmp_path / "blank.pdf"
        doc.save(str(pdf_path))
        doc.close()
        result = extract_text(pdf_path, "pdf")
        assert result == ""

    def test_extract_docx(self, tmp_path):
        from docx import Document
        doc = Document()
        doc.add_paragraph("Hello from docx")
        doc.add_paragraph("Second paragraph")
        p = tmp_path / "test.docx"
        doc.save(str(p))
        result = extract_text(p, "docx")
        assert "Hello from docx" in result
        assert "Second paragraph" in result

    def test_extract_xlsx(self, tmp_path):
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws["A1"] = "Quarterly"
        ws["B1"] = "Revenue"
        ws["A2"] = "Q1"
        ws["B2"] = 100
        p = tmp_path / "test.xlsx"
        wb.save(str(p))
        result = extract_text(p, "xlsx")
        assert "Quarterly" in result
        assert "Revenue" in result

    def test_skip_too_large_file(self, tmp_path):
        p = tmp_path / "large.txt"
        with p.open("wb") as f:
            f.seek((MAX_FILE_SIZE + 1))
            f.write(b"x")
        result = extract_text(p, "txt")
        assert result == ""

    def test_skip_unsupported_format(self, tmp_path):
        p = tmp_path / "test.xyz"
        p.write_text("content")
        assert extract_text(p, "xyz") == ""

    def test_text_capped_at_max_length(self, tmp_path):
        p = tmp_path / "long.txt"
        p.write_text("a" * (MAX_TEXT_LENGTH + 1000), encoding="utf-8")
        result = extract_text(p, "txt")
        assert len(result) <= MAX_TEXT_LENGTH
