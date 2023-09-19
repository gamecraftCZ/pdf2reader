import logging
import tkinter as tk

from src.pdf2reader.gui.crop_selector import CropSelector
from src.pdf2reader.gui.page_renderer import PageRenderer
from src.pdf2reader.pdf_file import PdfFile, PdfPage
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
        self.page_renderer = PageRenderer(self.window, max_width=-1, max_height=-1)
        self.page_renderer.set_page(self.page)

        self.page_edit_controls = PageEditControls(self.window, self.page_renderer.image_canvas, self.page, padx=5, pady=2)

        self.navigation_bar = NavigationBar(self.window, self.is_pdf_opened, self.current_page, self.page_count, height=30)

        self.page_edit_controls.pack(fill=tk.X, side=tk.TOP, expand=False)
        self.page_renderer.pack(fill=tk.BOTH, side=tk.TOP, expand=True)
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
    def __init__(self, parent, canvas: tk.Canvas, page: PdfPage, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.canvas = canvas
        self.page = page

        self.crop_selected_area = [tk.IntVar(), tk.IntVar(), tk.IntVar(), tk.IntVar()]
        if self.page.crop_area:
            # Be careful of pdf coordinate system is from bottom left
            self.crop_selected_area[0].set(self.page.crop_area[0])
            self.crop_selected_area[1].set(self.page.crop_area[3])
            self.crop_selected_area[2].set(self.page.crop_area[2])
            self.crop_selected_area[3].set(self.page.crop_area[1])

        self.crop_already_exists = self.page.crop_area is not None

        self.crop_button = tk.Button(self, text="Crop", command=self._crop_button_callback)
        self.cropping_label = tk.Label(self, text="Cropping...")
        self.crop_done_button = tk.Button(self, text="Apply crop", command=self._crop_done_button_callback)

        self.crop_button.pack(side=tk.RIGHT, expand=False)
        self.crop_selector = CropSelector(self.canvas, self.crop_selected_area, crop_already_exists=self.crop_already_exists,
                                          max_x=self.page.original_crop_area[2] - self.page.original_crop_area[0],
                                          max_y=self.page.original_crop_area[3] - self.page.original_crop_area[1])


    def _crop_button_callback(self):
        self.crop_button.pack_forget()
        self.crop_done_button.pack(side=tk.RIGHT, expand=False)
        self.cropping_label.pack(side=tk.RIGHT, expand=False)

        self.crop_selector.switch_to_cropping()

    def _crop_done_button_callback(self):
        self.crop_done_button.pack_forget()
        self.cropping_label.pack_forget()
        self.crop_button.pack(side=tk.RIGHT, expand=False)

        self.crop_selector.switch_to_indicator()

        if 0 == self.crop_selected_area[0].get() == self.crop_selected_area[2].get() == self.crop_selected_area[1].get() == self.crop_selected_area[3].get():
            return

        self.crop_already_exists = True
        self._crop_done(self.crop_selected_area[0].get(), self.crop_selected_area[1].get(),
                        self.crop_selected_area[2].get(), self.crop_selected_area[3].get())

    def _crop_done(self, x1: int, y1: int, x2: int, y2: int):
        self.page.crop_area = [x1, y2, x2, y1]
