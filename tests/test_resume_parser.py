import io
import pytest
from unittest.mock import MagicMock, patch


class TestParseResume:
    def test_raises_for_unsupported_extension(self):
        from app.utils.resume_parser import parse_resume
        with pytest.raises(ValueError, match="Unsupported file type"):
            parse_resume(b"data", "resume.txt")

    def test_parses_pdf(self):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "John Doe\nSoftware Engineer"
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = lambda s: mock_pdf
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page]

        with patch("app.utils.resume_parser.pdfplumber.open", return_value=mock_pdf):
            from app.utils.resume_parser import parse_resume
            result = parse_resume(b"%PDF-fake", "resume.pdf")

        assert "John Doe" in result
        assert "Software Engineer" in result

    def test_parses_docx(self):
        mock_para1 = MagicMock()
        mock_para1.text = "Jane Smith"
        mock_para2 = MagicMock()
        mock_para2.text = "Data Engineer"
        mock_para3 = MagicMock()
        mock_para3.text = ""  # empty paragraphs should be skipped

        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para1, mock_para2, mock_para3]

        with patch("app.utils.resume_parser.Document", return_value=mock_doc):
            from app.utils.resume_parser import parse_resume
            result = parse_resume(b"PK-fake", "resume.docx")

        assert "Jane Smith" in result
        assert "Data Engineer" in result
        assert result.count("\n") == 1  # empty paragraph not included

    def test_pdf_skips_none_pages(self):
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = None
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = lambda s: mock_pdf
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page1, mock_page2]

        with patch("app.utils.resume_parser.pdfplumber.open", return_value=mock_pdf):
            from app.utils.resume_parser import parse_resume
            result = parse_resume(b"%PDF-fake", "resume.pdf")

        assert result == "Page 1 content"
