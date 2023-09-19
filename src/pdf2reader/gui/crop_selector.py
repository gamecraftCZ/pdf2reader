import tkinter as tk
from typing import List


class CropSelector:
    def __init__(self, canvas: tk.Canvas, crop_selected_area: List[tk.IntVar] = None, crop_already_exists: bool = False,
                 max_x: int = 999999999, max_y: int = 999999999):
        """
        :type canvas: tk.Canvas
        :type crop_selected_area: List[tk.IntVar]  # [x1 (left), y1(top), x2(right), y2(bottom)]
        :param canvas:
        :param crop_selected_area:
        """
        self.canvas = canvas
        self.crop_selected_area = crop_selected_area
        self.max_x = max_x
        self.max_y = max_y

        self.crop_enabled = False

        self.canvas.bind("<ButtonPress-1>", self._drag_start)
        self.canvas.bind("<ButtonRelease-1>", self._drag_stop)
        self.canvas.bind("<B1-Motion>", self._drag)

        self.crop_indicator = None
        self.crop_created = crop_already_exists
        self.dragging = False
        self.drag_start_offset = [0, 0]
        self.drag_position = [0, 0]

        if self.crop_created:
            self.cap_crop_selected_area()
            self.crop_indicator = self.IndicatorSelection(self.canvas, [self.crop_selected_area[0].get(),
                                                                        self.crop_selected_area[1].get(),
                                                                        self.crop_selected_area[2].get(),
                                                                        self.crop_selected_area[3].get()])

    def _drag_start(self, event):
        if not self.crop_enabled:
            return

        if not self.crop_created:
            if self.crop_indicator:
                self.crop_indicator.destroy()
            self.crop_indicator = self.CroppingSelection(self.canvas)

            self.crop_selected_area[0].set(event.x)
            self.crop_selected_area[1].set(event.y)

            self.crop_created = True
            self.drag_start_offset = [0, 0]
            self.dragging_bottom_right = True
            self.dragging = True
            self.dragging_coordinates = [self.crop_selected_area[2], self.crop_selected_area[3]]

        else:
            self.dragging_coordinates = [None, None]

            left, top, right, bottom = (self.crop_selected_area[0].get(), self.crop_selected_area[1].get(),
                                        self.crop_selected_area[2].get(), self.crop_selected_area[3].get())

            if right - 20 < event.x < right + 5:
                self.dragging_coordinates[0] = self.crop_selected_area[2]
            elif left - 5 < event.x < left + 20:
                self.dragging_coordinates[0] = self.crop_selected_area[0]

            if bottom - 20 < event.y < bottom + 5:
                self.dragging_coordinates[1] = self.crop_selected_area[3]
            elif top - 5 < event.y < top + 20:
                self.dragging_coordinates[1] = self.crop_selected_area[1]

            self.drag_start_offset = [
                (event.x - self.dragging_coordinates[0].get()) if self.dragging_coordinates[0] else 0,
                (event.y - self.dragging_coordinates[1].get()) if self.dragging_coordinates[1] else 0]

            if self.dragging_coordinates[0] is None and self.dragging_coordinates[1] is None:
                if left < event.x < right and top < event.y < bottom:
                    self.drag_position = event.x, event.y
                    self.dragging = True
            else:
                self.dragging = True

    def _drag_stop(self, event):
        if not self.crop_enabled:
            return

        self.dragging = False
        rearange_coordinates_tkvars(self.crop_selected_area[0], self.crop_selected_area[1],
                                    self.crop_selected_area[2], self.crop_selected_area[3])

    def _drag(self, event):
        if not self.crop_enabled:
            return

        if self.dragging:
            if self.dragging_coordinates[0] is None and self.dragging_coordinates[1] is None:
                self.crop_selected_area[0].set(self.crop_selected_area[0].get() + (event.x - self.drag_position[0]))
                self.crop_selected_area[1].set(self.crop_selected_area[1].get() + (event.y - self.drag_position[1]))
                self.crop_selected_area[2].set(self.crop_selected_area[2].get() + (event.x - self.drag_position[0]))
                self.crop_selected_area[3].set(self.crop_selected_area[3].get() + (event.y - self.drag_position[1]))

                self.drag_position = event.x, event.y

            else:
                new_x = (event.x - self.drag_start_offset[0]) if self.dragging_coordinates[0] else None
                new_y = (event.y - self.drag_start_offset[1]) if self.dragging_coordinates[1] else None
                self.dragging_coordinates[0].set(new_x) if new_x else None
                self.dragging_coordinates[1].set(new_y) if new_y else None

            self.cap_crop_selected_area()
            self.crop_indicator.set_crop_location(self.crop_selected_area[0].get(), self.crop_selected_area[1].get(),
                                                  self.crop_selected_area[2].get(), self.crop_selected_area[3].get())

    def cap_crop_selected_area(self):
        self.crop_selected_area[0].set(max(0, self.crop_selected_area[0].get()))
        self.crop_selected_area[0].set(min(self.max_x, self.crop_selected_area[0].get()))

        self.crop_selected_area[1].set(max(0, self.crop_selected_area[1].get()))
        self.crop_selected_area[1].set(min(self.max_y, self.crop_selected_area[1].get()))

        self.crop_selected_area[2].set(max(0, self.crop_selected_area[2].get()))
        self.crop_selected_area[2].set(min(self.max_x, self.crop_selected_area[2].get()))

        self.crop_selected_area[3].set(max(0, self.crop_selected_area[3].get()))
        self.crop_selected_area[3].set(min(self.max_y, self.crop_selected_area[3].get()))

    def destroy(self):
        self.crop_indicator.destroy()

    def switch_to_cropping(self):
        if not self.crop_enabled:
            self.crop_enabled = True
            if self.crop_indicator:
                self.crop_indicator.destroy()
            if self.crop_created:
                self.crop_indicator = self.CroppingSelection(self.canvas)
                self.crop_indicator.set_crop_location(self.crop_selected_area[0].get(),
                                                      self.crop_selected_area[1].get(),
                                                      self.crop_selected_area[2].get(),
                                                      self.crop_selected_area[3].get())

    def switch_to_indicator(self):
        if self.crop_enabled:
            self.crop_enabled = False
            if self.crop_indicator:
                self.crop_indicator.destroy()
            if self.crop_created:
                self.crop_indicator = self.IndicatorSelection(self.canvas, [self.crop_selected_area[0].get(),
                                                                            self.crop_selected_area[1].get(),
                                                                            self.crop_selected_area[2].get(),
                                                                            self.crop_selected_area[3].get()])

    class CroppingSelection:
        def __init__(self, canvas: tk.Canvas):
            self.canvas = canvas

            self.top_left_rectangle = self.canvas.create_rectangle(0, 0, 0, 0, outline="red", width=2)
            self.bottom_right_rectangle = self.canvas.create_rectangle(0, 0, 0, 0, outline="green", width=2)
            self.main_rectangle = self.canvas.create_rectangle(0, 0, 0, 0, outline="black", width=2)

        def set_crop_location(self, x1, y1, x2, y2):
            x1, y1, x2, y2 = rearange_coordinates(x1, y1, x2, y2)
            self.canvas.coords(self.main_rectangle, x1, y1, x2, y2)
            self.canvas.coords(self.top_left_rectangle, x1, y1, x1 + 20, y1 + 20)
            self.canvas.coords(self.bottom_right_rectangle, x2 - 20, y2 - 20, x2, y2)

        def destroy(self):
            self.canvas.delete(self.top_left_rectangle)
            self.canvas.delete(self.bottom_right_rectangle)
            self.canvas.delete(self.main_rectangle)

    class IndicatorSelection:
        def __init__(self, canvas: tk.Canvas, crop_location: [int, int, int, int]):
            self.canvas = canvas

            x1, y1, x2, y2 = rearange_coordinates(crop_location[0], crop_location[1], crop_location[2],
                                                  crop_location[3])

            self.top_line = self.canvas.create_line(x1 - 10, y1,
                                                    x2 + 10, y1, fill="gray", width=2)
            self.bottom_line = self.canvas.create_line(x1 - 10, y2,
                                                       x2 + 10, y2, fill="gray", width=2)
            self.left_line = self.canvas.create_line(x1, y1 - 10,
                                                     x1, y2 + 10, fill="gray", width=2)
            self.right_line = self.canvas.create_line(x2, y1 - 10,
                                                      x2, y2 + 10, fill="gray", width=2)

        def set_crop_location(self, x1, y1, x2, y2):
            x1, y1, x2, y2 = rearange_coordinates(x1, y1, x2, y2)
            self.canvas.coords(self.top_line, x1 - 10, y1, x2 + 10, y1)
            self.canvas.coords(self.bottom_line, x1 - 10, y2, x2 + 10, y2)
            self.canvas.coords(self.left_line, x1, y1 - 10, x1, y2 + 10)
            self.canvas.coords(self.right_line, x2, y1 - 10, x2, y2 + 10)

        def destroy(self):
            self.canvas.delete(self.top_line)
            self.canvas.delete(self.bottom_line)
            self.canvas.delete(self.left_line)
            self.canvas.delete(self.right_line)


def rearange_coordinates(x1: int, y1: int, x2: int, y2: int) -> [int, int, int, int]:
    x1, x2 = (x1, x2) if x1 < x2 else (x2, x1)
    y1, y2 = (y1, y2) if y1 < y2 else (y2, y1)
    return x1, y1, x2, y2


def rearange_coordinates_tkvars(x1_var: tk.IntVar, y1_var: tk.IntVar, x2_var: tk.IntVar, y2_var: tk.IntVar):
    """
    Rearange coordinates so that x1 < x2 and y1 < y2
    """
    x1, y1, x2, y2 = rearange_coordinates(x1_var.get(), y1_var.get(), x2_var.get(), y2_var.get())
    x1_var.set(x1)
    y1_var.set(y1)
    x2_var.set(x2)
    y2_var.set(y2)
