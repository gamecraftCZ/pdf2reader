import logging
import tkinter as tk
from pathlib import Path
from threading import Thread
from tkinter import filedialog

from src.pdf2reader.gui.page_edit_window import PageEditWindow
from src.pdf2reader.gui.pdf_page_grid_display import PdfPageGridDisplay
from src.pdf2reader.pdf_file import PdfFile, PdfPage

logger = logging.getLogger(__name__)


class MainGUI(tk.Frame):
    def __init__(self, parent: tk.Tk, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        # Working variables
        self.pdf_file = None
        self._setup_variables()

        # GUI stuff
        self.root = parent
        self._create_menu()
        self._create_content()

    def _setup_variables(self):
        self.opened_pdf_name = tk.StringVar()

        self.current_page = tk.IntVar()
        self.page_count = tk.IntVar()
        self.is_pdf_opened = tk.BooleanVar()


    def _create_menu(self):
        self.menu_bar = tk.Menu(self)
        self.root.configure(menu=self.menu_bar)

        # File menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff=False)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)

        self.file_menu.add_command(label="Open PDF", command=self._open_file_button)
        self.file_menu.add_command(label="Save PDF", command=self._save_file_button)

    def _create_content(self):
        self.pdf_grid_display = PdfPageGridDisplay(self, self.is_pdf_opened, page_click_callback=self._open_page_edit_window,
                                                   create_page_additional_info=lambda master, page, page_number: tk.Label(master, text=f"{page_number + 1}"))
        self.pdf_grid_display.pack(fill=tk.BOTH, side=tk.TOP, expand=True)

    def _open_page_edit_window(self, page: PdfPage, page_number: int):
        PageEditWindow(self.pdf_file, page_number, close_callback=lambda: self.pdf_grid_display.reload_single_page_change_marks(page_number))

    def _open_file_button(self):
        path = filedialog.askopenfilename(title="Open PDF file", filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if not path:
            return
        Thread(target=self._open_file, args=(path,)).start()

    def _open_file(self, path):
        logger.debug(f"Opening pdf file: {path}")

        try:
            if self.pdf_file is not None:  # To free up memory
                del self.pdf_file
            self.is_pdf_opened.set(False)

            self.current_page.set(0)

            self.pdf_file = PdfFile.open(path, progressbar=True)
            self.page_count.set(self.pdf_file.page_count)
            self.is_pdf_opened.set(True)
            self.opened_pdf_name.set(Path(path).name)
            self.root.title("PDF2Reader - " + self.opened_pdf_name.get())

            self.pdf_grid_display.set_pdf_file(self.pdf_file)

        except Exception as e:
            logger.exception(f"Failed to open pdf file: {path}")
            tk.messagebox.showerror("Error", "Failed to open pdf file: " + str(e))


    def _save_file_button(self):
        print("TODO Save file")
