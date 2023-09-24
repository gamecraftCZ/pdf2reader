import logging
import tkinter as tk

from pdf2reader.gui.page_renderer import PageRenderer
from pdf2reader.pdf_file import PdfFile

logger = logging.getLogger(__name__)


class PdfDisplay(tk.Frame):
    def __init__(self, parent: tk.Frame, is_pdf_opened: tk.BooleanVar, current_page: tk.IntVar, page_count: tk.IntVar, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.page_renderer = PageRenderer(self)
        self.page_renderer.pack(fill=tk.BOTH, side=tk.TOP, expand=True)

        self.pdf_file: PdfFile or None = None

        self.is_pdf_opened = is_pdf_opened
        self.current_page = current_page
        self.page_count = page_count
        self._setup_variables()

    def _setup_variables(self):
        self.current_page.trace("w", lambda *args: self.update_page())
        self.is_pdf_opened.trace("w", lambda *args: self.update_page())

    def update_page(self):
        logger.debug(f"Updating page to page number: {self.current_page.get()}")
        if self.pdf_file:
            self.page_renderer.set_page(self.pdf_file.get_page(self.current_page.get()), self.current_page.get())
            self.page_renderer.set_boxes(self.pdf_file.get_boxes(self.current_page.get()))

    def set_pdf_file(self, pdf_file):
        self.pdf_file = pdf_file
        self.update_page()
