import tkinter as tk
from tkinter import ttk
from typing import Callable


class ImageOptimizationWindow:
    def __init__(self, optimize_callback: Callable[[int, bool, bool], None]):
        self._optimize_callback = optimize_callback

        self.window = tk.Toplevel()
        self.window.grab_set()
        self.window.title("Optimize images")
        self.window.geometry("400x220")

        self._setup_variables()
        self._setup_layout()

    def _setup_variables(self):
        self.image_quality = tk.IntVar()
        self.image_quality.set(30)

        self.should_resize_images = tk.BooleanVar()
        self.should_resize_images.set(True)

        self.should_remove_images = tk.BooleanVar()
        self.should_remove_images.set(False)

    def _setup_layout(self):
        self.quality_frame = tk.Frame(self.window, padx=10, pady=10)
        self.quality_frame.pack(fill=tk.X, side=tk.TOP, expand=False)
        self.image_quality_label = tk.Label(self.quality_frame, text="Image quality (0-100):")
        self.image_quality_label.pack(pady=10, side=tk.LEFT)
        self.image_quality_scale = tk.Scale(self.quality_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                            variable=self.image_quality)
        self.image_quality_scale.pack(pady=10, side=tk.LEFT, fill=tk.X, expand=True)

        self.should_resize_images_checkbox = tk.Checkbutton(self.window,
                                                            text="Resize images to lower resolution that still matches the page",
                                                            variable=self.should_resize_images)
        self.should_resize_images_checkbox.pack(side=tk.TOP, pady=10)

        self.should_remove_images_checkbox = tk.Checkbutton(self.window,
                                                            text="Remove all images",
                                                            variable=self.should_remove_images)
        self.should_remove_images_checkbox.pack(side=tk.TOP, pady=10)

        self.buttons_frame = tk.Frame(self.window)
        self.buttons_frame.pack(fill=tk.NONE, side=tk.TOP, expand=False)
        self.optimize_button = tk.Button(self.buttons_frame, text="Optimize", command=self._optimize_button)
        self.optimize_button.pack(pady=10, padx=10, side=tk.LEFT, expand=False)
        self.cancel_button = tk.Button(self.buttons_frame, text="Cancel", command=self.close)
        self.cancel_button.pack(pady=10, padx=10, side=tk.LEFT, expand=False)

    def _optimize_button(self):
        self._optimize_callback(self.image_quality.get(), self.should_resize_images.get(),
                                self.should_remove_images.get())
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        self.window.grab_release()
        self.window.destroy()
