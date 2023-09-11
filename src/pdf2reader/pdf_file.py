import pikepdf


class PdfFile:
    def __init__(self, pdf: pikepdf.Pdf, path: str = None):
        self.path = path
        self.pdf = pdf

    @staticmethod
    def open(path: str) -> "PdfFile":
        pdf = pikepdf.open(path)
        pdf_file = PdfFile(pdf, path)
        return pdf_file
