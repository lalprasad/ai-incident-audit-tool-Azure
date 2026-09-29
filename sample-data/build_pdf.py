"""Render sample-data/multi-ticket.txt into a text-layer PDF."""

from __future__ import annotations

from pathlib import Path

from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "multi-ticket.txt"
DEST = ROOT / "multi-ticket.pdf"
PAGE_SIZE = (1100, 1400)
MARGIN = 48
LINE_HEIGHT = 12


def build(source: Path = SOURCE, dest: Path = DEST) -> Path:
    text = source.read_text(encoding="utf-8")
    pdf = canvas.Canvas(str(dest), pagesize=PAGE_SIZE)
    width, height = PAGE_SIZE
    y = height - MARGIN
    pdf.setFont("Courier", 9)
    for line in text.splitlines():
        if y < MARGIN:
            pdf.showPage()
            pdf.setFont("Courier", 9)
            y = height - MARGIN
        pdf.drawString(MARGIN, y, line)
        y -= LINE_HEIGHT
    pdf.save()
    return dest


if __name__ == "__main__":
    print(build())
