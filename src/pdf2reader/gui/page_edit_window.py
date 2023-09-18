import logging
import tkinter as tk

from src.pdf2reader.gui.page_renderer import PageRenderer
from src.pdf2reader.pdf_file import PdfFile
from src.pdf2reader.gui.navigation_bar import NavigationBar

logger = logging.getLogger(__name__)

class PageEditWindow:
    def __init__(self, pdf_file: PdfFile, page_number: int):
        self.pdf_file = pdf_file
        self.page = self.pdf_file.pages_parsed[page_number]

        self._setup_variables()
        self.is_pdf_opened.set(True)
        self.current_page.set(page_number)
        self.page_count.set(self.pdf_file.page_count)

        self.window = tk.Toplevel()
        self.window.grab_set()
        self.window.title("Edit Page")

        self.page_renderer = PageRenderer(self.window, max_width=-1, max_height=-1)
        self.page_renderer.pack(fill=tk.BOTH, side=tk.TOP, expand=True)
        self.page_renderer.set_page(self.page.get_page())

        self.navigation_bar = NavigationBar(self.window, self.is_pdf_opened, self.current_page, self.page_count, height=30)
        self.navigation_bar.pack(fill=tk.X, side=tk.BOTTOM, expand=False)

        self.window.geometry(f"{self.page_renderer.rendered_page.width() + 20}x{self.page_renderer.rendered_page.height() + 40}")

        self._setup_variable_listeners()

    def _setup_variables(self):
        self.is_pdf_opened = tk.BooleanVar()
        self.current_page = tk.IntVar()
        self.page_count = tk.IntVar()

    def _setup_variable_listeners(self):
        self.current_page.trace("w", lambda *args: self.update_page())
        self.is_pdf_opened.trace("w", lambda *args: self.update_page())

    def update_page(self):
        logger.debug(f"Updating page to page number: {self.current_page.get()}")
        if self.pdf_file:
            self.page_renderer.set_page(self.pdf_file.get_page(self.current_page.get()))
            self.page_renderer.set_boxes(self.pdf_file.get_boxes(self.current_page.get()))

    def __del__(self):
        self.close()

    def close(self):
        self.window.grab_release()
        self.window.destroy()
