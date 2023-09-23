import logging
import tkinter as tk
from typing import Callable, List

from src.pdf2reader.data_structures import Box
from src.pdf2reader.gui.page_renderer import PageRenderer
from src.pdf2reader.gui.select_pages_to_action_window import SelectPagesToActionWindow
from src.pdf2reader.pdf_file import PdfFile, Section

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

        self.update_page()

        self.window.geometry(
            f"{self.page_renderer.rendered_page.width() + 20}x{self.page_renderer.rendered_page.height() + 65}")
        self.window.protocol("WM_DELETE_WINDOW", self._close_callback)

    def _close_callback(self):
        self.close()
        if self.close_callback:
            self.close_callback()

    def _setup_layout(self):
        self.page_renderer = PageRenderer(self.window, max_width=-1, max_height=-1)

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
            self._update_boxes()

    def _update_boxes(self):
        boxes = []
        page = self.pdf_file.get_page(self.current_page.get())
        for section in page.sections:
            box: Box = section.get_bounding_box(page_height=float(page.original_crop_area[3]))
            if not box:
                continue
            box.on_click = lambda click_loc, section=section: self._box_clicked_callback(click_loc, section)
            boxes.append(box)
        self.page_renderer.set_boxes(boxes)

    def _box_clicked_callback(self, click_loc, section: Section):
        logger.debug(f"Box clicked for {section}")
        keep_var = tk.BooleanVar()
        keep_var.set(section.keep_in_output)

        popup = tk.Menu(self.page_renderer, tearoff=0)

        popup.add_radiobutton(label="Keep section", value=True, variable=keep_var,  # command=_edit_section_keep,)
                              command=lambda: self._edit_section_keep(section, keep=True))
        popup.add_radiobutton(label="Remove section", value=False, variable=keep_var,  # command=option_selected,)
                              command=lambda: self._edit_section_keep(section, keep=False))
        popup.add_separator()
        popup.add_command(label=f"Edit on {len(section.section_group.sections) if section.section_group else 1} pages",
                          command=lambda: self._edit_section_on_pages(section))

        popup.tk_popup(click_loc[0], click_loc[1])

    def _edit_section_keep(self, section: Section, keep: bool):
        section.keep_in_output = keep
        self._update_boxes()

    def _edit_section_on_pages(self, section: Section):
        logger.debug("Edit section on pages button clicked")
        pages_to_keep = [s.page_number for s in section.section_group.sections if s.keep_in_output]
        SelectPagesToActionWindow("Select pages where to keep the section", self.pdf_file,
                                  save_callback=lambda selected: self._edit_section_on_pages_callback(selected,
                                                                                                      section.section_group.sections),
                                  checkbox_text="Keep section", preselected_pages=pages_to_keep,
                                  enabled_pages=[s.page_number for s in section.section_group.sections],
                                  show_crop=False, show_sections=True,
                                  show_sections_only_from_group=section.section_group)
        self.close()

    def _edit_section_on_pages_callback(self, selected_pages: List[int], sections: List[Section]):
        logger.debug(f"Edit section on pages callback: {selected_pages}, out of sections: {sections}")

        for section in sections:
            section.keep_in_output = section.page_number in selected_pages

        if self.reload_all_pages_callback:
            self.reload_all_pages_callback()

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

        self.page_renderer.set_boxes([])
        self.page_renderer.crop_renderer.switch_to_cropping()

    def _crop_done_button_callback(self):
        self.crop_done_button.pack_forget()
        self.cropping_label.pack_forget()
        self.crop_button.pack(side=tk.RIGHT, expand=False)

        self.page_renderer.crop_renderer.switch_to_indicator()

        if (0 == self.page_renderer.crop_selected_area[0].get() == self.page_renderer.crop_selected_area[2].get()
                == self.page_renderer.crop_selected_area[1].get() == self.page_renderer.crop_selected_area[3].get()):
            self.page_renderer.set_boxes(self.pdf_file.get_boxes(self.page_number))
            return

        # Opening select pages action window is non blocking!
        SelectPagesToActionWindow("Select pages to crop", self.pdf_file, save_callback=self._save_callback,
                                  checkbox_text="Crop", preselected_pages=[self.page_number],
                                  show_crop=True, custom_crop=[
                        self.page_renderer.crop_selected_area[0].get(), self.page_renderer.crop_selected_area[1].get(),
                        self.page_renderer.crop_selected_area[2].get(), self.page_renderer.crop_selected_area[3].get()
                    ],
                                  show_sections=False, show_sections_only_from_group=None)

        self.master.destroy()

    def _save_callback(self, selected_pages: List[int]):
        x1, y1, x2, y2 = self.page_renderer.crop_selected_area[0].get(), self.page_renderer.crop_selected_area[1].get(), \
            self.page_renderer.crop_selected_area[2].get(), self.page_renderer.crop_selected_area[3].get()

        for page_number in selected_pages:
            page = self.pdf_file.get_page(page_number)
            page.crop_area = [x1, page.original_height - y1, x2, page.original_height - y2]

        if self.page_number in selected_pages:
            self.crop_already_exists = True

        if self.reload_all_pages_callback:
            self.reload_all_pages_callback()
