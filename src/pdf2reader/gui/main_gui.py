import logging
import tkinter as tk
from pathlib import Path
from threading import Thread
from tkinter import filedialog

import pikepdf

from pdf2reader.gui.image_optimization_window import ImageOptimizationWindow
from pdf2reader.gui.page_edit_window import PageEditWindow
from pdf2reader.gui.pdf_page_grid_display import PdfPageGridDisplay
from pdf2reader.pdf_file import PdfFile, PdfPage

logger = logging.getLogger(__name__)


class MainGUI(tk.Frame):
    def __init__(self, parent: tk.Tk, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        # Working variables
        self.pdf_file: PdfFile or None = None
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
        self.file_menu.add_command(label="Save PDF", command=self._save_file_button, state=tk.DISABLED)

        # Edit menu
        self.edit_menu = tk.Menu(self.menu_bar, tearoff=False)
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu)

        self.edit_menu.add_command(label="Optimize images", command=self._optimize_images_button, state=tk.DISABLED)

    def _create_content(self):
        self.pdf_grid_display = PdfPageGridDisplay(self, self.is_pdf_opened, show_sections=True,
                                                   page_click_callback=self._open_page_edit_window,
                                                   create_page_additional_info=lambda master, page,
                                                                                      page_number: tk.Label(master,
                                                                                                            text=f"{page_number + 1}"))
        self.pdf_grid_display.pack(fill=tk.BOTH, side=tk.TOP, expand=True)

    def _open_page_edit_window(self, page: PdfPage, page_number: int):
        PageEditWindow(self.pdf_file, page_number,
                       close_callback=lambda: self.pdf_grid_display.reload_single_page_change_marks(page_number),
                       reload_all_pages_callback=lambda: self.pdf_grid_display.reload_all_pages_change_marks())

    def _open_file_button(self):
        path = filedialog.askopenfilename(title="Open PDF file",
                                          filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if not path:
            return
        Thread(target=self._open_file, args=(path,)).start()

    def _open_file(self, path: str):
        logger.info(f"Opening pdf file: {path}")

        try:
            if self.pdf_file is not None:  # To free up memory
                 self.pdf_file = None
            self.is_pdf_opened.set(False)

            self.current_page.set(0)

            self.pdf_file = PdfFile.open(path, progressbar=True, ask_password=True)
            self.page_count.set(self.pdf_file.page_count)
            self.is_pdf_opened.set(True)
            self.opened_pdf_name.set(Path(path).name)
            self.root.title("PDF2Reader - " + self.opened_pdf_name.get())

            self.pdf_grid_display.set_pdf_file(self.pdf_file)

            self.file_menu.entryconfig(1, state=tk.NORMAL)
            self.edit_menu.entryconfig(0, state=tk.NORMAL)

            if tk.messagebox.askyesno("Image optimization", "Optimize images in PDF file?"):
                self._optimize_images_button()

        except pikepdf.PasswordError:
            logger.warning("Wrong password for pdf file")
            tk.messagebox.showerror("Wrong password", f"Wrong password for pdf file '{path}'")

        except Exception as e:
            logger.exception(f"Failed to open pdf file: {path}")
            tk.messagebox.showerror("Error", "Failed to open pdf file: " + str(e))

    def _save_file_button(self):
        if not self.pdf_file:
            tk.messagebox.showerror("Error", "No PDF file opened, so none can be saved")
            return
        path = filedialog.asksaveasfilename(title="Save PDF file",
                                            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if not path:
            return
        Thread(target=self._save_file, args=(path,)).start()

    def _save_file(self, path: str):
        logger.info(f"Saving pdf file to: {path}")

        try:
            if not self.pdf_file:
                tk.messagebox.showerror("Error", "No PDF file opened, so none can be saved")
                return

            self.pdf_file.save(path, progressbar=True)

        except Exception as e:
            logger.exception(f"Failed to save pdf file: {path}")
            tk.messagebox.showerror("Error", "Failed to save pdf file: " + str(e))

    def _optimize_images_button(self):
        if not self.pdf_file:
            tk.messagebox.showerror("Error", "No PDF file opened, so none can be optimized")
            return

        opt_fn = lambda image_quality, should_resize_images, should_remove_images: Thread(target=self._optimize_images,
                                                                                          args=(image_quality,
                                                                                                should_resize_images,
                                                                                                should_remove_images)).start()

        ImageOptimizationWindow(opt_fn)

    def _optimize_images(self, image_quality: int = 30, should_resize_images: bool = True, should_remove_images: bool = False):
        logger.info(f"Optimizing images in pdf file")

        try:
            if not self.pdf_file:
                tk.messagebox.showerror("Error", "No PDF file opened, so none can be optimized")
                return

            self.pdf_file.optimize_images(images_quality=image_quality, should_resize_images=should_resize_images,
                                          should_remove_images=should_remove_images, progressbar=True)
            tk.messagebox.showinfo("Images optimized", "Images optimized")

        except Exception as e:
            logger.exception(f"Failed to optimize images in pdf file")
            tk.messagebox.showerror("Error", "Failed to optimize images in pdf file: " + str(e))
