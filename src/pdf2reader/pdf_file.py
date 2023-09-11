from typing import List

import pikepdf

from src.pdf2reader.data_structures import Box


class PdfFile:
    def __init__(self, pdf: pikepdf.Pdf, path: str = None):
        self.path = path
        self.pdf = pdf

    @staticmethod
    def open(path: str) -> "PdfFile":
        pdf = pikepdf.open(path)
        pdf_file = PdfFile(pdf, path)
        return pdf_file

    @property
    def page_count(self) -> int:
        return len(self.pdf.pages)

    def get_page(self, page_number: int) -> pikepdf.Page:
        return self.pdf.pages[page_number]

    def get_boxes(self, page_number: int) -> List[Box]:
        # TODO: Implement this
        return [Box(250, 150, 450, 250, "red", lambda: print("Clicked"))]
