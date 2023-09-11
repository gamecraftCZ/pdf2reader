import logging
import tkinter as tk
from tkinter import ttk

logger = logging.getLogger(__name__)


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
