import io
import logging
import tkinter as tk
import pikepdf
import fitz
from pathlib import Path
from tkinter import ttk, filedialog

from src.pdf2reader.pdf_file import PdfFile

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
        logger.debug("Opening pdf file:", path)
        self.pdf_file = PdfFile.open(path)
        self.pdf_display.set_pdf_file(self.pdf_file)

        self.current_page.set(0)
        self.page_count.set(self.pdf_file.page_count)
        self.is_pdf_opened.set(True)

        self.opened_pdf_name.set(Path(path).name)
        self.root.title("PDF2Reader - " + self.opened_pdf_name.get())

        self.pdf_display.update_page()



    def _save_file(self):
        print("TODO Save file")

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



class NavigationBar(tk.Frame):
    def __init__(self, parent: tk.Frame, is_pdf_opened: tk.BooleanVar, current_page: tk.IntVar, page_count: tk.IntVar, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.current_page = current_page
        self.current_page.trace("w", lambda *args: self._update_page_number_text())

        self.page_count = page_count
        self.page_count.trace("w", lambda *args: self._update_page_number_text())

        self.is_pdf_opened = is_pdf_opened
        self.is_pdf_opened.trace("w", lambda *args: self._update_page_number_text())
        self.is_pdf_opened.trace("w", lambda *args: self._update_buttons_state())

        self.page_number_text = tk.StringVar()
        self._create_bar()

        self._update_page_number_text()
        self._update_buttons_state()


    def _update_page_number_text(self):
        if self.is_pdf_opened.get():
            self.page_number_text.set(f"Page {self.current_page.get() + 1}/{self.page_count.get()}")
        else:
            self.page_number_text.set("Open PDF file using File -> Open PDF")

    def _update_buttons_state(self):
        if self.is_pdf_opened.get():
            self.left_button.configure(state=tk.NORMAL)
            self.right_button.configure(state=tk.NORMAL)
        else:
            self.left_button.configure(state=tk.DISABLED)
            self.right_button.configure(state=tk.DISABLED)

    def _create_bar(self):
        self.left_button = ttk.Button(self, text="<-", command=self._left_button)
        self.left_button.pack(side=tk.LEFT, fill=tk.Y, expand=False)

        self.page_number = tk.Label(self, textvariable=self.page_number_text)
        self.page_number.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.right_button = ttk.Button(self, text="->", command=self._right_button)
        self.right_button.pack(side=tk.RIGHT, fill=tk.Y, expand=False)

    def _left_button(self):
        if self.current_page.get() > 0:
            self.current_page.set(self.current_page.get() - 1)

    def _right_button(self):
        if self.current_page.get() < self.page_count.get() - 1:
            self.current_page.set(self.current_page.get() + 1)

