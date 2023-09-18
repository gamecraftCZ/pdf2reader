import io
import logging
import tkinter as tk
from tkinter import ttk
from typing import List

import fitz
import pikepdf

from src.pdf2reader.data_structures import Box
from src.pdf2reader.gui.page_renderer import PageRenderer

logger = logging.getLogger(__name__)


class PdfDisplay(tk.Frame):
    def __init__(self, parent: tk.Frame, is_pdf_opened: tk.BooleanVar, current_page: tk.IntVar, page_count: tk.IntVar, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.page_renderer = PageRenderer(self)
        self.page_renderer.pack(fill=tk.BOTH, side=tk.TOP, expand=True)

        self.pdf_file = None

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
            self.page_renderer.set_page(self.pdf_file.get_page(self.current_page.get()))
            self.page_renderer.set_boxes(self.pdf_file.get_boxes(self.current_page.get()))

    def set_pdf_file(self, pdf_file):
        self.pdf_file = pdf_file
        self.update_page()
