"""
Geriye uyumluluk shim'i — PDF rapor üreticisi `reporting/pdf.py` modülüne taşındı.

Yeni kod `from reporting.pdf import ReportMeta, build_pdf_report` kullanmalıdır.
"""

from reporting.pdf import (  # noqa: F401
    ReportMeta,
    build_pdf_report,
    reportlab_available,
)

__all__ = ["ReportMeta", "build_pdf_report", "reportlab_available"]
