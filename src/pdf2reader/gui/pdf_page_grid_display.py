import logging
import tkinter as tk
from typing import Callable, List

from pdf2reader.gui.debouncer import Debouncer
from pdf2reader.gui.page_renderer import PageRenderer
from pdf2reader.gui.progress_bar_window import ProgressBarWindow
from pdf2reader.gui.vertical_scrolled_frame import VerticalScrolledFrame
from pdf2reader.pdf_file import PdfPage, PdfFile, SectionGroup

logger = logging.getLogger(__name__)


class PdfPageGridDisplay(tk.Frame):
    def __init__(self, parent: tk.Frame or tk.Tk or tk.Toplevel, is_pdf_opened: tk.BooleanVar, pdf_file: PdfFile = None,
                 create_page_additional_info: Callable[[tk.Widget, PdfPage, int], tk.Widget] = None,
                 page_click_callback: Callable[[PdfPage, int], None] = None, show_crop: bool = True,
                 custom_crop: List[int] = None, show_sections: bool = False,
                 show_sections_only_from_group: SectionGroup = None, enabled_pages: List[int] = None,
                 *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self._create_page_additional_info = create_page_additional_info
        self._show_crop = show_crop
        self._custom_crop = custom_crop
        self._show_sections_only_from_group = show_sections_only_from_group
        self._show_sections = show_sections
        self._enabled_pages = enabled_pages

        self.verticalscroll = VerticalScrolledFrame(self)
        self.verticalscroll.pack(fill=tk.BOTH, side=tk.TOP, expand=True)

        self.scrollframe = tk.Frame(self.verticalscroll.interior)  # This is our GRID frame
        self.scrollframe.pack(fill=tk.BOTH, side=tk.TOP, expand=True)

        self.pdf_file: PdfFile or None = pdf_file
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
                                             create_page_additional_info=self._create_page_additional_info,
                                             default_click_callback=(lambda e, page=page, page_number=page_number:
                                                                     self.page_click_callback(page, int(page_number)))
                                             if self.page_click_callback else None,
                                             show_crop=self._show_crop, custom_crop=self._custom_crop,
                                             disabled=page_number not in self._enabled_pages if self._enabled_pages is not None else False)
                page_renderer.set_page(self.pdf_file.get_page(page_number), page_number)

                if self._show_sections:
                    if self._show_sections_only_from_group:
                        boxes = []
                        for section in self.pdf_file.get_page(page_number).sections:
                            if section.section_group == self._show_sections_only_from_group:
                                box = section.get_bounding_box(page_height=float(page.original_crop_area[3]),
                                                               cap_area=page.original_crop_area)
                                if box:
                                    boxes.append(box)
                        page_renderer.set_boxes(boxes)
                    else:
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

    def set_pdf_file(self, pdf_file: PdfFile):
        self.pdf_file = pdf_file
        self._pdf_opened_change()

    def reload_single_page_change_marks(self, page_number: int):
        self._page_renderers[page_number].reload_change_marks()

    def reload_all_pages_change_marks(self):
        for page_renderer in self._page_renderers:
            page_renderer.reload_change_marks()
