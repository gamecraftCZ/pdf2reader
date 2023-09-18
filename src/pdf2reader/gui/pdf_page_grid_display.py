import io
import logging
import time
import tkinter as tk
from tkinter import ttk
from typing import List

import fitz
import pikepdf
from PIL import Image, ImageTk

from src.pdf2reader.data_structures import Box
from src.pdf2reader.gui.debouncer import Debouncer
from src.pdf2reader.gui.progress_bar_window import ProgressBarWindow
from src.pdf2reader.gui.vertical_scrolled_frame import VerticalScrolledFrame

logger = logging.getLogger(__name__)


class PdfPageGridDisplay(tk.Frame):
    def __init__(self, parent: tk.Frame, is_pdf_opened: tk.BooleanVar, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.verticalscroll = VerticalScrolledFrame(self)
        self.verticalscroll.pack(fill=tk.BOTH, side=tk.TOP, expand=True)

        self.scrollframe = tk.Frame(self.verticalscroll.interior)  # This is our GRID frame
        self.scrollframe.pack(fill=tk.BOTH, side=tk.TOP, expand=True)

        self.pdf_file = None

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
                page = self.pdf_file.get_page(page_number)

                page_renderer = PageRenderer(self.scrollframe, padx=5, pady=5)
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


class PageRenderer(tk.Frame):
    def __init__(self, parent: tk.Frame, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self._create_image_canvas()
        self.height = -1
        self.width = -1
        self.scale = 1

        self.max_height = 256
        self.max_width = 256

        self.padx = kwargs.get("padx", 0)
        self.pady = kwargs.get("pady", 0)

        self.rendered_page = None
        self.boxes = []

    def _create_image_canvas(self):
        self.image_canvas = tk.Canvas(self, background="gray", height=300, width=300)
        self.image_canvas.bind("<Button-1>", self._clicked)
        self.image_canvas.pack(fill=tk.X, side=tk.TOP, expand=False)

    def _get_page_as_image(self, page: pikepdf.Page) -> tuple[tk.PhotoImage, float]:
        pdf_stream = io.BytesIO()
        pdf = pikepdf.Pdf.new()
        pdf.pages.append(page)
        pdf.save(pdf_stream)

        ftz = fitz.open(stream=pdf_stream)
        page = ftz.load_page(0)
        ix = page.get_pixmap()
        imgdata = ix.tobytes("ppm")

        img = Image.open(io.BytesIO(imgdata))

        if img.height / self.max_height > img.width / self.max_width:
            new_height = self.max_height
            new_width = img.width / img.height * self.max_height
        else:
            new_height = img.height / img.width * self.max_width
            new_width = self.max_width

        scale = new_width / img.width
        img = img.resize((int(new_width), int(new_height)))

        photo_img = ImageTk.PhotoImage(img)

        return photo_img, scale

    def set_page(self, page: pikepdf.Page):
        if not page:
            self.rendered_page = None
            self.image_canvas.delete(tk.ALL)
            return

        try:
            self.rendered_page, self.scale = self._get_page_as_image(page)

            self.image_canvas.delete(tk.ALL)
            logger.debug(f"Setting image canvas to height: {self.rendered_page.height()}, width: {self.rendered_page.width()}")
            self.image_canvas.config(height=self.rendered_page.height(), width=self.rendered_page.width())
            self.height = self.rendered_page.height() + 2 * self.padx
            self.width = self.rendered_page.width() + 2 * self.pady

            self.image_canvas.create_image(0, 0, anchor='nw', image=self.rendered_page)
            self.image_canvas.image = self.rendered_page

        except Exception as e:
            logger.exception(f"Failed to render page")
            tk.messagebox.showerror("Error", "Failed to render page: " + str(e))

    def set_boxes(self, boxes: List[Box]):
        self.boxes = boxes

        for box in boxes:
            self.image_canvas.create_rectangle(box.x0 * self.scale, box.y0 * self.scale,
                                               box.x1 * self.scale, box.y1 * self.scale,
                                               outline=box.color, width=2)

    def _clicked(self, event):
        print("clicked at", event.x, event.y)
        if self.rendered_page:
            for box in self.boxes:
                if box.x0 < event.x < box.x1 and box.y0 < event.y < box.y1:
                    popup = tk.Menu(self, tearoff=0)
                    popup.add_command(label="Main Product")
                    popup.add_command(label="Side Product")
                    try:
                        popup.tk_popup(event.x + self.winfo_rootx(), event.y + self.winfo_rooty(), 0)
                    finally:
                        popup.grab_release()
                    # box.on_click()
                    break
