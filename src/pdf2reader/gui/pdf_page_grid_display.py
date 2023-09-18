import io
import logging
import time
import tkinter as tk
from tkinter import ttk
from typing import List, Callable

import fitz
import pikepdf
from PIL import Image, ImageTk

from src.pdf2reader.data_structures import Box
from src.pdf2reader.gui.debouncer import Debouncer
from src.pdf2reader.gui.page_renderer import PageRenderer
from src.pdf2reader.gui.progress_bar_window import ProgressBarWindow
from src.pdf2reader.gui.vertical_scrolled_frame import VerticalScrolledFrame
from src.pdf2reader.pdf_file import PdfPage

logger = logging.getLogger(__name__)


class PdfPageGridDisplay(tk.Frame):
    def __init__(self, parent: tk.Frame, is_pdf_opened: tk.BooleanVar,
                 page_click_callback: Callable[[PdfPage, int], None] = None, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.verticalscroll = VerticalScrolledFrame(self)
        self.verticalscroll.pack(fill=tk.BOTH, side=tk.TOP, expand=True)

        self.scrollframe = tk.Frame(self.verticalscroll.interior)  # This is our GRID frame
        self.scrollframe.pack(fill=tk.BOTH, side=tk.TOP, expand=True)

        self.pdf_file = None
        self.page_click_callback = page_click_callback

        self.is_pdf_opened = is_pdf_opened
        self._page_renderers = []
        self._setup_variables()
        self._prepare_pages()
        self._pack_pages_to_grid()
        self._pdf_opened_change()

        self._resize_debouncer = Debouncer(lambda event: self._pack_pages_to_grid())
        self.bind("<Configure>", self._resize_debouncer.process_event)

    def _setup_variables(self):
        # self.current_page.trace("w", lambda *args: self.update_page())
        self.is_pdf_opened.trace("w", lambda *args: self._pdf_opened_change())

    def _prepare_pages(self):
        for page_renderer in self._page_renderers:
            page_renderer.grid_forget()
            page_renderer.destroy()
        self._page_renderers = []
        if self.pdf_file:
            progress_bar = ProgressBarWindow("Rendering PDF", "Rendering PDF...", 0, self.pdf_file.page_count)
            for page_number in range(self.pdf_file.page_count):
                page_number = page_number
                page = self.pdf_file.get_page(page_number)

                page_renderer = PageRenderer(self.scrollframe, padx=5, pady=5,
                                             default_click_callback=(lambda e, page=page, page_number=page_number:
                                                                     self.page_click_callback(page, int(page_number)))
                                                                if self.page_click_callback else None)
                page_renderer.set_page(page)
                page_renderer.set_boxes(self.pdf_file.get_boxes(page_number))

                self._page_renderers.append(page_renderer)
                progress_bar.update_progress(page_number)
                progress_bar.update_message(f"Rendering PDF pages... page {page_number + 1}/{self.pdf_file.page_count}")
            progress_bar.close()


    def _pack_pages_to_grid(self):
        column = 0
        max_columns = 1
        cur_width = 0
        for page_renderer in self._page_renderers:
            cur_width += page_renderer.width
            if cur_width > self.winfo_width() - 30:
                column = 0
            else:
                column += 1
                max_columns = max(max_columns, column)


        row = 0
        column = 0
        for page_renderer in self._page_renderers:
            if column + 1 > max_columns:
                row += 1
                column = 0

            page_renderer.grid_forget()
            page_renderer.grid(row=row, column=column)
            column += 1

        logger.debug("Created new grid layout")

    def _pdf_opened_change(self):
        logger.debug("Rendering new PDF grid display")
        if self.pdf_file:
            self._prepare_pages()
            self._pack_pages_to_grid()

    def set_pdf_file(self, pdf_file):
        self.pdf_file = pdf_file
        self._pdf_opened_change()

    def _open_page_edit_window(self, page_number: int):
        logger.info(f"Opening page edit window for page {page_number}")
        self.pdf_file.open_page_edit_window(page_number)

