import io
import logging
import tkinter as tk
from typing import List, Callable

import fitz
import pikepdf
from PIL import Image, ImageTk

from src.pdf2reader.data_structures import Box

logger = logging.getLogger(__name__)

class PageRenderer(tk.Frame):
    def __init__(self, parent: tk.Frame or tk.Toplevel or tk.Tk, default_click_callback: Callable = None,
                 max_height: int = 256, max_width: int = 256, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.height = -1
        self.width = -1
        self.scale = 1

        self.max_height = max_height
        self.max_width = max_width

        self.padx = kwargs.get("padx", 0)
        self.pady = kwargs.get("pady", 0)

        self.rendered_page = None
        self.boxes = []
        self.default_click_callback = default_click_callback

        self._create_image_canvas()
        if self.default_click_callback:
            self.image_canvas.config(cursor="hand1")

    def _create_image_canvas(self):
        self.image_canvas = tk.Canvas(self, background="gray", height=300, width=300)
        self.image_canvas.bind("<Button-1>", self._clicked_canvas)
        self.image_canvas.pack(side=tk.TOP, expand=False)

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

        new_width, new_height = img.width, img.height
        if self.max_height > -1 and img.height / self.max_height > img.width / self.max_width:
            new_height = self.max_height
            new_width = img.width / img.height * self.max_height
        elif self.max_width > -1:
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
            self.image_canvas.config(height=self.rendered_page.height()-2, width=self.rendered_page.width()-2)
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

    def _clicked_canvas(self, event):
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
                    # box.on_click()  # TODO
                    break
            else:
                if self.default_click_callback:
                    self.default_click_callback(event)
