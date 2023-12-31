import logging
import tkinter as tk
from typing import List, Callable

from PIL import ImageTk
from PIL import Image

from pdf2reader.data_structures import Box
from pdf2reader.gui.crop_selector import CropSelector
from pdf2reader.pdf_file import PdfPage

logger = logging.getLogger(__name__)


class PageRenderer(tk.Frame):
    def __init__(self, parent: tk.Frame or tk.Toplevel or tk.Tk,
                 create_page_additional_info: Callable[[tk.Widget, PdfPage, int], tk.Widget] = None,
                 default_click_callback: Callable = None, max_height: int = 256, max_width: int = 256,
                 show_crop: bool = True, custom_crop: List[int] = None, disabled: bool = False,
                 *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.create_page_additional_info = create_page_additional_info
        self._show_crop = show_crop
        self._custom_crop = custom_crop
        self._disabled = disabled

        self.height = -1
        self.width = -1
        self.scale = 1

        self.max_height = max_height
        self.max_width = max_width

        self.padx = kwargs.get("padx", 0)
        self.pady = kwargs.get("pady", 0)

        self.page: PdfPage or None = None
        self.page_number = -1

        self.rendered_page = None
        self.additional_info = None
        self.boxes = []
        self._rendered_boxes = []
        self.default_click_callback = default_click_callback

        self.crop_selected_area = [tk.IntVar(), tk.IntVar(), tk.IntVar(), tk.IntVar()]
        self.crop_renderer = None

        self._create_image_canvas()

        if self.default_click_callback:
            self.image_canvas.config(cursor="hand1")

    def _create_image_canvas(self):
        self.image_canvas = tk.Canvas(self, background="gray", height=300, width=300)
        self.image_canvas.bind("<Button-1>", self._clicked_canvas)
        self.image_canvas.pack(side=tk.TOP, expand=False)

    def _get_page_as_image(self, page: PdfPage, disabled: bool = False) -> tuple[tk.PhotoImage, float]:
        img: Image = page.get_original_rendered_image()

        new_width, new_height = img.width, img.height
        if self.max_height > -1 and img.height / self.max_height > img.width / self.max_width:
            new_height = self.max_height
            new_width = img.width / img.height * self.max_height
        elif self.max_width > -1:
            new_height = img.height / img.width * self.max_width
            new_width = self.max_width

        scale = new_width / img.width
        img = img.resize((int(new_width), int(new_height)))

        if disabled:
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 128))
            img = Image.alpha_composite(img.convert("RGBA"), overlay)

        photo_img = ImageTk.PhotoImage(img)

        return photo_img, scale

    def set_page(self, page: PdfPage, page_number: int):
        if not page:
            self.rendered_page = None
            self.image_canvas.delete(tk.ALL)
            if self.crop_renderer:
                self.crop_renderer.destroy()
            return

        try:
            self.page = page
            self.page_number = page_number
            self.rendered_page, self.scale = self._get_page_as_image(page, disabled=self._disabled)

            self.image_canvas.delete(tk.ALL)
            self.image_canvas.config(height=self.rendered_page.height() - 2, width=self.rendered_page.width() - 2)
            self.height = self.rendered_page.height() + 2 * self.padx
            self.width = self.rendered_page.width() + 2 * self.pady

            self.image_canvas.create_image(0, 0, anchor='nw', image=self.rendered_page)
            self.image_canvas.image = self.rendered_page

            # Crop renderer
            if self.crop_renderer:
                self.crop_renderer.destroy()

            if self._custom_crop:
                self.crop_selected_area[0].set(self._custom_crop[0] * self.scale)
                self.crop_selected_area[1].set((page.original_height - self._custom_crop[1]) * self.scale)
                self.crop_selected_area[2].set(self._custom_crop[2] * self.scale)
                self.crop_selected_area[3].set((page.original_height - self._custom_crop[3]) * self.scale)
            elif page.crop_area:
                self.crop_selected_area[0].set(page.crop_area[0] * self.scale)
                self.crop_selected_area[1].set((page.original_height - page.crop_area[1]) * self.scale)
                self.crop_selected_area[2].set(page.crop_area[2] * self.scale)
                self.crop_selected_area[3].set((page.original_height - page.crop_area[3]) * self.scale)

            if self._show_crop:
                self.crop_renderer = CropSelector(self.image_canvas, self.crop_selected_area,
                                                  crop_already_exists=bool(page.crop_area) or bool(self._custom_crop),
                                                  max_x=page.original_crop_area[2] - page.original_crop_area[0],
                                                  max_y=page.original_crop_area[3] - page.original_crop_area[1])

            if self.additional_info:
                self.additional_info.pack_forget()
            if self.create_page_additional_info:
                if not self._disabled:
                    self.additional_info = self.create_page_additional_info(self, self.page, self.page_number)
                    self.additional_info.pack(fill=tk.X, side=tk.TOP, expand=False)

        except Exception as e:
            logger.exception(f"Failed to render page")
            tk.messagebox.showerror("Error", "Failed to render page: " + str(e))

    def set_boxes(self, boxes: List[Box]):
        self.boxes = boxes
        self._render_boxes()

    def _render_boxes(self):
        for rendered_box in self._rendered_boxes:
            self.image_canvas.delete(rendered_box)
        self._rendered_boxes = []
        for box in self.boxes:
            self._rendered_boxes.append(self.image_canvas.create_rectangle(box.x0 * self.scale, box.y0 * self.scale,
                                                                           box.x1 * self.scale, box.y1 * self.scale,
                                                                           outline=box.color, width=2))

    def reload_change_marks(self):
        if self.page:
            self.set_boxes(self.page.get_boxes())
            if self.page.crop_area and self.crop_renderer:
                self.crop_renderer.set_crop_area(self.page.crop_area[0] * self.scale,
                                                 (self.page.original_height - self.page.crop_area[1]) * self.scale,
                                                 self.page.crop_area[2] * self.scale,
                                                 (self.page.original_height - self.page.crop_area[3]) * self.scale)

    def _clicked_canvas(self, event):
        logger.debug(f"Clicked canvas at: {event.x}, {event.y}, disabled: {self._disabled}")
        if not self._disabled:
            if self.rendered_page:
                for box in self.boxes:
                    if (box.x0 < event.x < box.x1 or box.x0 > event.x > box.x1) and \
                            (box.y0 < event.y < box.y1 or box.y0 > event.y > box.y1):
                        box.on_click([event.x + self.winfo_rootx(), event.y + self.winfo_rooty()])
                        break
                else:
                    if self.default_click_callback:
                        self.default_click_callback(event)
