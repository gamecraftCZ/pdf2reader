import logging
import tkinter as tk
from typing import Callable, List

from pdf2reader.gui.pdf_page_grid_display import PdfPageGridDisplay
from pdf2reader.gui.tooltip import create_tooltip
from pdf2reader.pdf_file import PdfFile, SectionGroup

logger = logging.getLogger(__name__)


class SelectPagesToActionWindow:
    def __init__(self, title: str, pdf_file: PdfFile, save_callback: Callable[[List[int]], None],
                 checkbox_text: str = "", preselected_pages: List[int] = None,
                 enabled_pages: List[int] = None, show_crop: bool = True, custom_crop: List[int] = None,
                 show_sections: bool = False, show_sections_only_from_group: SectionGroup = None):
        self.pdf_file = pdf_file
        self.checkbox_text = checkbox_text
        self.save_callback = save_callback
        self._preselected_pages = preselected_pages
        self._enabled_pages = enabled_pages
        self._show_crop = show_crop
        self._custom_crop = custom_crop
        self._show_sections = show_sections
        self._show_section_only_from_group = show_sections_only_from_group

        self.window = tk.Toplevel()
        try:
            self.window.grab_set()  # Fails on some platforms (works on Windows)
        except:
            pass
        self.window.title(title)
        self.window.geometry("900x600")
        self.window.protocol("WM_DELETE_WINDOW", self._close_callback)

        self.page_checkboxes = {}

        self._setup_variables()
        self._setup_layout()

        for page_number in self._preselected_pages:
            self.page_checkboxes[page_number].select()

    def _setup_variables(self):
        self.is_pdf_opened = tk.BooleanVar()

        self.is_pdf_opened.set(True)

    def _setup_layout(self):
        self.controls = ControlsMenu(self.window, self.pdf_file, select_callback=self._select_callback_1_indexed,
                                     unselect_callback=self._unselect_callback_1_indexed,
                                     save_callback=self._save_callback)
        self.pages_view = PdfPageGridDisplay(self.window, is_pdf_opened=self.is_pdf_opened, pdf_file=self.pdf_file,
                                             create_page_additional_info=self._create_page_additional_info,
                                             show_crop=self._show_crop, custom_crop=self._custom_crop,
                                             show_sections=self._show_sections,
                                             show_sections_only_from_group=self._show_section_only_from_group,
                                             enabled_pages=self._enabled_pages)

        self.controls.pack(fill=tk.X, side=tk.TOP, expand=False)
        self.pages_view.pack(fill=tk.BOTH, side=tk.TOP, expand=True)

    def _save_callback(self):
        selected_pages = []
        for page_number, checkbox in self.page_checkboxes.items():
            checked_status = int(checkbox.getvar(checkbox.cget('variable')))
            if checked_status:
                selected_pages.append(page_number)
        self.save_callback(selected_pages)
        self.close()

    def _select_callback_1_indexed(self, page_numbers: List[int]):
        invalid_page_indexes = []
        for page_number in page_numbers:
            checkbox = self.page_checkboxes.get(page_number - 1)
            if checkbox:
                checkbox.select()
            else:
                if page_number < 1 or page_number > self.pdf_file.page_count:
                    invalid_page_indexes.append(page_number)
        if invalid_page_indexes:
            if len(invalid_page_indexes) > 20:
                invalid_page_indexes = invalid_page_indexes[:20] + ["..."]
            tk.messagebox.showerror("Invalid page indexes", f"Invalid page indexes: {invalid_page_indexes}. "
                                                            f"Ignoring them and selecting the rest.")

    def _unselect_callback_1_indexed(self, page_numbers: List[int]):
        invalid_page_indexes = []
        for page_number in page_numbers:
            checkbox = self.page_checkboxes.get(page_number - 1)
            if checkbox:
                checkbox.deselect()
            else:
                if page_number < 1 or page_number > self.pdf_file.page_count:
                    invalid_page_indexes.append(page_number)
        if invalid_page_indexes:
            if len(invalid_page_indexes) > 20:
                invalid_page_indexes = invalid_page_indexes[:20] + ["..."]
            tk.messagebox.showerror("Invalid page indexes", f"Invalid page indexes: {invalid_page_indexes}. "
                                                            f"Ignoring them and selecting the rest.")

    def _create_page_additional_info(self, master, page, page_number):
        frame = tk.Frame(master, padx=5)
        frame.pack(fill=tk.NONE, side=tk.TOP, expand=False)

        label = tk.Label(frame, text=f"page {page_number + 1} • ")
        label.pack(side=tk.LEFT, padx=0)

        checkbox = tk.Checkbutton(frame, text=self.checkbox_text, command=lambda: self._checkbox_callback(page_number))
        checkbox.pack(side=tk.LEFT, padx=0)

        self.page_checkboxes[page_number] = checkbox

        return frame

    def _checkbox_callback(self, page_number):
        checkbox = self.page_checkboxes[page_number]
        checked_status = checkbox.getvar(checkbox.cget('variable'))
        logger.debug(f"checkbox callback: {page_number}, status: {checked_status}")

    def _close_callback(self):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        try:
            self.window.grab_release()
        except:
            pass
        self.window.destroy()


class ControlsMenu(tk.Frame):
    def __init__(self, parent, pdf_file: PdfFile, select_callback: Callable[[List[int]], None],
                 unselect_callback: Callable[[List[int]], None], save_callback: Callable, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.pdf_file = pdf_file

        self.parent = parent
        self.select_callback = select_callback
        self.unselect_callback = unselect_callback
        self.save_callback = save_callback

        self._setup_layout()

    def _setup_layout(self):
        self.range_label = tk.Label(self, text="Range: ")
        self.tooltip_label = tk.Label(self, text="?")
        create_tooltip(self.tooltip_label, "Select pages for cropping. "
                                           "Use comma to separate page numbers. "
                                           "Use dash to specify a range (inclusive). "
                                           "Use ':' to specify a step. "
                                           "Use '*' to select all pages. "
                                           "For example '1,3,5-9:2' will select pages 1, 3, 5, 7, 9.")

        self.inputfield = tk.Entry(self)

        self.crop_button = tk.Button(self, text="Select range", command=self._select_button_callback)
        self.uncrop_button = tk.Button(self, text="Unselect range", command=self._unselect_button_callback)
        self.splitter = tk.Label(self, text=" | ")
        self.save_button = tk.Button(self, text="Save", command=self._save_button_callback)

        self.range_label.pack(side=tk.LEFT, padx=5)
        self.tooltip_label.pack(side=tk.LEFT, padx=5)
        self.inputfield.pack(side=tk.LEFT, padx=5)
        self.crop_button.pack(side=tk.LEFT, padx=5)
        self.uncrop_button.pack(side=tk.LEFT, padx=5)
        self.splitter.pack(side=tk.LEFT, padx=5)
        self.save_button.pack(side=tk.LEFT, padx=5)

    def _parse_select_text(self, select_text: str) -> List[int]:
        page_numbers = []
        if "*" in select_text:
            return list(range(1, 1 + self.pdf_file.page_count))
        for part in select_text.split(","):
            if "-" in part:
                start, end = part.split("-")
                if ":" in end:
                    end, step = end.split(":")
                else:
                    step = 1
                page_numbers.extend(range(int(start), int(end) + 1, int(step)))
            else:
                page_numbers.append(int(part))
        return page_numbers

    def _select_button_callback(self):
        select_text = self.inputfield.get()
        logger.debug(f"Select button callback text: {select_text}")
        try:
            # Parse select text to list of page numbers
            page_numbers = self._parse_select_text(select_text)
            logger.debug(f"Select button callback parsed page numbers (1-indexed): {page_numbers}")
            self.select_callback(page_numbers)
        except Exception as e:
            logger.error(f"Select button callback error: {e}")
            tk.messagebox.showerror("Invalid range", f"Invalid range: '{select_text}', error: {str(e)}")

    def _unselect_button_callback(self):
        select_text = self.inputfield.get()
        logger.debug(f"Unselect button callback text: {select_text}")
        try:
            # Parse select text to list of page numbers
            page_numbers = self._parse_select_text(select_text)
            logger.debug(f"Unselect button callback parsed page numbers (1-indexed): {page_numbers}")
            self.unselect_callback(page_numbers)
        except Exception as e:
            logger.error(f"Unselect button callback error: {e}")
            tk.messagebox.showerror("Invalid range", f"Invalid range: '{select_text}', error: {str(e)}")

    def _save_button_callback(self):
        self.save_callback()
