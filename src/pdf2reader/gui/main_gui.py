import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from src.pdf2reader.gui.navigation_bar import NavigationBar
from src.pdf2reader.gui.pdf_display import PdfDisplay
from src.pdf2reader.pdf_file import PdfFile

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

        self.file_menu.add_command(label="Open PDF", command=self._open_file)
        self.file_menu.add_command(label="Save PDF", command=self._save_file)

    def _create_content(self):
        self.pdf_display = PdfDisplay(self, self.is_pdf_opened, self.current_page, self.page_count)
        self.pdf_display.pack(fill=tk.BOTH, side=tk.TOP, expand=True)

        self.navigation_bar = NavigationBar(self, self.is_pdf_opened, self.current_page, self.page_count, height=30)
        self.navigation_bar.pack(fill=tk.X, side=tk.BOTTOM, expand=False)


    def _open_file(self):
        path = filedialog.askopenfilename(title="Open PDF file", filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if not path:
            return

        logger.debug("Opening pdf file:", path)

        try:
            if self.pdf_file is not None:  # To free up memory
                del self.pdf_file

            self.pdf_file = PdfFile.open(path)
            self.pdf_display.set_pdf_file(self.pdf_file)

            self.current_page.set(0)
            self.page_count.set(self.pdf_file.page_count)
            self.is_pdf_opened.set(True)

            self.opened_pdf_name.set(Path(path).name)
            self.root.title("PDF2Reader - " + self.opened_pdf_name.get())

            self.pdf_display.update_page()

        except Exception as e:
            logger.exception("Failed to open pdf file:", path)
            tk.messagebox.showerror("Error", "Failed to open pdf file: " + str(e))


    def _save_file(self):
        print("TODO Save file")
