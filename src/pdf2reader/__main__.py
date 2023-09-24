import importlib.resources
import logging
import tkinter as tk
from pdf2reader.gui.main_gui import MainGUI
import sys


def main():
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    root_window = tk.Tk()
    root_window.title("PDF2Reader")
    root_window.geometry("900x600")
    root_window.minsize(150, 50)

    icon = importlib.resources.files("pdf2reader").joinpath("assets").joinpath("pdf2reader_128x128.png").read_bytes()
    icon_image = tk.PhotoImage(data=icon)

    root_window.iconphoto(True, icon_image)

    app = MainGUI(root_window, borderwidth=3)
    app.pack(fill=tk.BOTH, expand=True)
    root_window.mainloop()


if __name__ == "__main__":
    main()
