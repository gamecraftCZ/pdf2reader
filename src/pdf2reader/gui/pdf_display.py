import io
import logging
import tkinter as tk
from tkinter import ttk
from typing import List

import fitz
import pikepdf

from src.pdf2reader.data_structures import Box

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
        logger.debug("Updating page to page number:", self.current_page.get())
        self.page_renderer.set_page(self.pdf_file.get_page(self.current_page.get()))
        self.page_renderer.set_boxes(self.pdf_file.get_boxes(self.current_page.get()))

    def set_pdf_file(self, pdf_file):
        self.pdf_file = pdf_file
        self.update_page()


class PageRenderer(tk.Frame):
    def __init__(self, parent: tk.Frame, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self._create_image_canvas()
        self.height = -1
        self.width = -1

        self.rendered_page = None
        self.boxes = []

    def _create_image_canvas(self):
        self.image_canvas = tk.Canvas(self, background="gray")
        self.image_canvas.pack(fill=tk.BOTH, side=tk.TOP, expand=True)

        self.image_canvas.bind('<Button-1>', self._clicked)

    def _get_page_as_image(self, page: pikepdf.Page) -> tk.PhotoImage:
        pdf_stream = io.BytesIO()
        pdf = pikepdf.Pdf.new()
        pdf.pages.append(page)
        pdf.save(pdf_stream)

        ftz = fitz.open(stream=pdf_stream)
        page = ftz.load_page(0)
        ix = page.get_pixmap()
        imgdata = ix.tobytes("ppm")
        img_file = tk.PhotoImage(data=imgdata)

        return img_file

    def set_page(self, page: pikepdf.Page):
        if not page:
            self.rendered_page = None
            self.image_canvas.delete(tk.ALL)
            return

        try:
            self.rendered_page = self._get_page_as_image(page)

            self.image_canvas.delete(tk.ALL)
            self.image_canvas.create_image(0, 0, anchor='nw', image=self.rendered_page)
            self.image_canvas.image = self.rendered_page
            # TODO scrollable canvas for rendered PDF page

            self.height = self.rendered_page.height()
            self.width = self.rendered_page.width()

        except Exception as e:
            logger.exception(f"Failed to render page")
            tk.messagebox.showerror("Error", "Failed to render page: " + str(e))

    def set_boxes(self, boxes: List[Box]):
        self.boxes = boxes

        for box in boxes:
            self.image_canvas.create_rectangle(box.x0, box.y0, box.x1, box.y1, outline=box.color, width=2)

    def _clicked(self, event):
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

