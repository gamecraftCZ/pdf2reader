import logging
import tkinter as tk
from src.pdf2reader.gui.main_gui import MainGUI
import sys


def main():
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    root_window = tk.Tk()
    root_window.title("PDF2Reader")
    root_window.geometry("800x600")
    root_window.iconbitmap("assets/pdf2reader_128x128.ico")
    root_window.minsize(100, 50)

    # root_window.overrideredirect(True)
    # root_window.attributes("-alpha", 0.01)

    app = MainGUI(root_window, borderwidth=3)
    app.pack(fill=tk.BOTH, expand=True)
    root_window.mainloop()


if __name__ == "__main__":
    main()
