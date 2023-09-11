import io
import logging
import tkinter as tk
from tkinter import ttk
import fitz
import pikepdf

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

    def set_pdf_file(self, pdf_file):
        self.pdf_file = pdf_file
        self.update_page()


class PageRenderer(tk.Frame):
    def __init__(self, parent: tk.Frame, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self._create_image_canvas()

    def _create_image_canvas(self):
        self.image_canvas = tk.Canvas(self, background="gray")
        self.image_canvas.pack(fill=tk.BOTH, side=tk.TOP, expand=True)


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
        img = self._get_page_as_image(page)
        self.image_canvas.delete(tk.ALL)
        self.image_canvas.create_image(0, 0, anchor='nw', image=img)
        self.image_canvas.image = img
        # TODO scrollable canvas for rendered PDF page
