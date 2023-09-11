import tkinter as tk
from tkinter import ttk

class MainGUI(ttk.Frame):
    def __init__(self, parent: tk.Tk, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)

        # Working variables
        self.pdf_file = None
        self.opened_pdf_name = tk.StringVar()

        # GUI stuff
        self.root = parent
        self._create_menu()
        self._create_content()

    def _create_menu(self):
        self.menu_bar = tk.Menu(self.root)
        self.root.configure(menu=self.menu_bar)

        # File menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff=False)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)

        self.file_menu.add_command(label="Open PDF", command=self._open_file)
        self.file_menu.add_command(label="Save PDF", command=self._save_file)

    def _create_content(self):
        self.pdf_display = PdfDisplay(self.root, background="yellow")
        self.pdf_display.pack(fill=tk.BOTH, side=tk.TOP, expand=True)

        self.navigation_bar = NavigationBar(self.root, background="lightblue", height=30)
        self.navigation_bar.pack(fill=tk.X, side=tk.BOTTOM, expand=False)


    def _open_file(self):
        print("TODO Open file")

    def _save_file(self):
        print("TODO Save file")


class PdfDisplay(tk.Frame):
    def __init__(self, parent: tk.Tk, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)


class NavigationBar(tk.Frame):
    def __init__(self, parent: tk.Tk, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
