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

        self.window = tk.Toplevel()
        self.window.grab_set()
        self.window.title("Edit Page")

        self._setup_variables(is_pdf_opened=True, current_page=page_number, page_count=self.pdf_file.page_count)
        self._setup_layout()
        self._setup_variable_listeners()

        self.window.geometry(f"{self.page_renderer.rendered_page.width() + 20}x{self.page_renderer.rendered_page.height() + 65}")

    def _setup_layout(self):
        self.page_edit_controls = PageEditControls(self.window, padx=5, pady=2)
        self.page_edit_controls.pack(fill=tk.X, side=tk.TOP, expand=False)

        self.page_renderer = PageRenderer(self.window, max_width=-1, max_height=-1)
        self.page_renderer.pack(fill=tk.BOTH, side=tk.TOP, expand=True)
        self.page_renderer.set_page(self.page)

        self.navigation_bar = NavigationBar(self.window, self.is_pdf_opened, self.current_page, self.page_count, height=30)
        self.navigation_bar.pack(fill=tk.X, side=tk.BOTTOM, expand=False)

    def _setup_variables(self, is_pdf_opened: bool, current_page: int, page_count: int):
        self.is_pdf_opened = tk.BooleanVar()
        self.current_page = tk.IntVar()
        self.page_count = tk.IntVar()

        self.is_pdf_opened.set(is_pdf_opened)
        self.current_page.set(current_page)
        self.page_count.set(page_count)

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


class PageEditControls(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.crop_button = tk.Button(self, text="Crop")
        self.crop_button.pack(side=tk.RIGHT, expand=False)
