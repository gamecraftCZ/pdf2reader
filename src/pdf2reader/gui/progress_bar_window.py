import tkinter as tk
from tkinter import ttk


class ProgressBarWindow:
    def __init__(self, title: str, message: str, current_value: int, max_value: int, on_cancel_callback=None):
        self.opened = False
        self.window = tk.Toplevel()
        self.window.grab_set()

        self.window.title(title)
        self.window.geometry("400x100")
        self.window.resizable(False, False)

        self.label = tk.Label(self.window, text=message)
        self.label.pack(pady=10)
        self.progress_bar = ttk.Progressbar(self.window, orient=tk.HORIZONTAL,
                                            length=200, mode="determinate",
                                            value=current_value, maximum=max_value)

        self.progress_bar.pack(pady=10)

        self._cancel_callback = on_cancel_callback
        if on_cancel_callback:
            self.cancel_button = tk.Button(self.window, text="Cancel", command=self._callback)
            self.cancel_button.pack(pady=10)
        self.window.protocol("WM_DELETE_WINDOW", self._callback)

    def _callback(self):
        if self._cancel_callback:
            self._cancel_callback()

    def update_message(self, new_message: str) -> None:
        self.label.config(text=new_message)

    def update_progress(self, new_progress: int) -> None:
        self.progress_bar.config(value=new_progress)

    def __del__(self):
        self.close()

    def close(self):
        self.window.grab_release()
        self.window.destroy()
