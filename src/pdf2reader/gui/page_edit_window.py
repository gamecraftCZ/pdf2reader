import logging
import tkinter as tk
from typing import Callable, List

from src.pdf2reader.gui.crop_selector import CropSelector
from src.pdf2reader.gui.page_renderer import PageRenderer
from src.pdf2reader.gui.select_pages_to_action_window import SelectPagesToActionWindow
from src.pdf2reader.pdf_file import PdfFile, PdfPage
from src.pdf2reader.gui.navigation_bar import NavigationBar

logger = logging.getLogger(__name__)


class PageEditWindow:
    def __init__(self, pdf_file: PdfFile, page_number: int, close_callback: Callable = None,
                 reload_all_pages_callback: Callable = None):
        self.pdf_file = pdf_file
        self.page = self.pdf_file.pages_parsed[page_number]
        self.close_callback = close_callback
        self.reload_all_pages_callback = reload_all_pages_callback

        self.window = tk.Toplevel()
        self.window.grab_set()
        self.window.title("Edit Page")

        self._setup_variables(is_pdf_opened=True, current_page=page_number, page_count=self.pdf_file.page_count)
        self._setup_layout()
        self._setup_variable_listeners()

        self.window.geometry(
            f"{self.page_renderer.rendered_page.width() + 20}x{self.page_renderer.rendered_page.height() + 65}")
        self.window.protocol("WM_DELETE_WINDOW", self._close_callback)

    def _close_callback(self):
        self.close()
        if self.close_callback:
            self.close_callback()

    def _setup_layout(self):
        self.page_renderer = PageRenderer(self.window, max_width=-1, max_height=-1)
        self.page_renderer.set_page(self.page, self.current_page.get())
        self.page_renderer.set_boxes(self.pdf_file.get_boxes(self.current_page.get()))

        self.page_edit_controls = PageEditControls(self.window, self.page_renderer.image_canvas,
                                                   self.current_page.get(),
                                                   self.pdf_file, self.page_renderer, padx=5, pady=2,
                                                   reload_all_pages_callback=self.reload_all_pages_callback)

        # self.navigation_bar = NavigationBar(self.window, self.is_pdf_opened, self.current_page, self.page_count, height=30)

        self.page_edit_controls.pack(fill=tk.X, side=tk.TOP, expand=False)
        self.page_renderer.pack(fill=tk.BOTH, side=tk.TOP, expand=True)
        # self.navigation_bar.pack(fill=tk.X, side=tk.BOTTOM, expand=False)

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
            self.page_renderer.set_page(self.pdf_file.get_page(self.current_page.get()), self.current_page.get())
            self.page_renderer.set_boxes(self.pdf_file.get_boxes(self.current_page.get()))

    def __del__(self):
        self.close()

    def close(self):
        self.window.grab_release()
        self.window.destroy()


class PageEditControls(tk.Frame):
    def __init__(self, parent, canvas: tk.Canvas, page_number: int, pdf_file: PdfFile, page_renderer: PageRenderer,
                 reload_all_pages_callback: Callable = None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.canvas = canvas
        self.pdf_file = pdf_file
        self.page_number = page_number
        self.page = pdf_file.get_page(page_number)
        self.page_renderer = page_renderer
        self.reload_all_pages_callback = reload_all_pages_callback

        self.crop_already_exists = self.page.crop_area is not None

        self.crop_button = tk.Button(self, text="Crop", command=self._crop_button_callback)
        self.cropping_label = tk.Label(self, text="Cropping...")
        self.crop_done_button = tk.Button(self, text="Apply crop", command=self._crop_done_button_callback)

        self.crop_button.pack(side=tk.RIGHT, expand=False)

    def _crop_button_callback(self):
        self.crop_button.pack_forget()
        self.crop_done_button.pack(side=tk.RIGHT, expand=False)
        self.cropping_label.pack(side=tk.RIGHT, expand=False)

        self.page_renderer.crop_renderer.switch_to_cropping()

    def _crop_done_button_callback(self):
        self.crop_done_button.pack_forget()
        self.cropping_label.pack_forget()
        self.crop_button.pack(side=tk.RIGHT, expand=False)

        self.page_renderer.crop_renderer.switch_to_indicator()

        if (0 == self.page_renderer.crop_selected_area[0].get() == self.page_renderer.crop_selected_area[2].get()
                == self.page_renderer.crop_selected_area[1].get() == self.page_renderer.crop_selected_area[3].get()):
            return

        # Opening select pages action window is non blocking!
        SelectPagesToActionWindow("Select pages to crop", self.pdf_file, save_callback=self._save_callback,
                                  checkbox_text="Crop", preselected_pages=[self.page_number])

    def _save_callback(self, selected_pages: List[int]):
        x1, y1, x2, y2 = self.page_renderer.crop_selected_area[0].get(), self.page_renderer.crop_selected_area[1].get(), \
            self.page_renderer.crop_selected_area[2].get(), self.page_renderer.crop_selected_area[3].get()

        for page_number in selected_pages:
            page = self.pdf_file.get_page(page_number)
            page.crop_area = [x1, y2, x2, y1]

        if self.page_number in selected_pages:
            self.crop_already_exists = True
        else:
            pass  # TODO: Revert rendered page crop if this page is not the one cropped

        if self.reload_all_pages_callback:
            self.reload_all_pages_callback()

    def _crop_done(self, x1: int, y1: int, x2: int, y2: int):
        self.page.crop_area = [x1, y2, x2, y1]
