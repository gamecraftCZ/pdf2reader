import io
import logging
from enum import Enum
from typing import List

import fitz
import numpy as np
import pikepdf
from PIL import Image

from src.pdf2reader.data_structures import Box

logger = logging.getLogger(__name__)


class SectionGroup:
    pass  # TODO SectionGrouping

class PdfPage:
    def __init__(self, page: pikepdf.Page):
        self._page = page
        self._parsed_stream = pikepdf.parse_content_stream(self._page)

        self._original_content = pikepdf.unparse_content_stream(self._parsed_stream)
        self._original_rendered = self.render_page_as_image(self._page)

        self.sections = self._parse_sections(pikepdf.parse_content_stream(self._page))
        # if "/Contents" in self._page.keys():
        #     del self._page["/Contents"]

        self.original_crop_area = [self._page.mediabox[0], self._page.mediabox[1], self._page.mediabox[2], self._page.mediabox[3]]

        self.crop_area = None

    class Section:
        # Section information
        typ: "SectionType"
        content: List[pikepdf.ContentStreamInstruction]
        location: List[float] or None
        additional: dict or None

        # Section output options
        keep_in_output: bool
        section_group: SectionGroup or None


        class SectionType(Enum):
            TEXT = "text"
            OTHER = "other"

        def __init__(self, typ: SectionType, content: List[pikepdf.ContentStreamInstruction], location: List[float] = None, additional: dict = None, keep_in_output: bool = True):
            self.typ = typ
            self.content = content
            self.keep_in_output = keep_in_output
            self.location = location
            self.additional = additional

        def get_bounding_box(self, page_height: float) -> Box or None:
            if self.typ == PdfPage.Section.SectionType.TEXT:
                if self.location is None:
                    logger.warning("WARNING: Text section has no location!")
                    return None

                return Box(self.location[0] - 5, page_height - self.location[1],
                           self.location[0] + self.additional["font_size"] * 1.2 + 5, page_height - self.location[1] - self.additional["font_size"] * 1.2 + 5,
                           color="lightgreen" if self.keep_in_output else "red", on_click=lambda: print("Clicked on text box!"))

        def __repr__(self):
            return f"Section(type={self.typ}, len={len(self.content)})"

    @property
    def original_height(self) -> int:
        return int(self._page.mediabox[3] - self._page.mediabox[1])

    @property
    def original_width(self) -> int:
        return int(self._page.mediabox[2] - self._page.mediabox[0])

    @staticmethod
    def _parse_sections(parsed_stream: List[pikepdf.ContentStreamInstruction]):
        sections = []

        current_section_type = PdfPage.Section.SectionType.OTHER
        current_section_content = []

        current_transformation_matrix = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float64)
        current_text_matrix = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float64)
        current_font = ("default_font", 11)  # Some random default value  (name, size)
        text_draw_relative_location = [0, 0]
        text_draw_location = None

        for instruction in parsed_stream:
            if instruction.operator == pikepdf.Operator("BT"):  # Begin text section
                if current_section_content:
                    sections.append(PdfPage.Section(current_section_type, current_section_content))

                if current_section_type == PdfPage.Section.SectionType.TEXT:
                    logger.warning("WARNING: text_section already started!")

                current_section_content = [instruction]
                current_section_type = PdfPage.Section.SectionType.TEXT
                current_text_matrix = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float64)
                text_draw_relative_location = [0, 0]
                text_draw_location = None

            elif instruction.operator == pikepdf.Operator("ET"):  # End text section
                current_section_content.append(instruction)

                if current_section_type != PdfPage.Section.SectionType.TEXT:
                    logger.warning("WARNING: text_section not started, but now ending!")

                if text_draw_location:
                    sections.append(PdfPage.Section(PdfPage.Section.SectionType.TEXT, current_section_content,
                                                    text_draw_location, {"font": current_font[0], "font_size": current_font[1]}))
                text_draw_location = None
                current_section_content = []
                current_section_type = PdfPage.Section.SectionType.OTHER

            elif instruction.operator == pikepdf.Operator("Tf"):  # Set font and font size
                current_section_content.append(instruction)
                current_font = (str(instruction.operands[0]), float(instruction.operands[1]))

            elif instruction.operator == pikepdf.Operator("Td"):  # Move text draw position
                current_section_content.append(instruction)
                ops = instruction.operands
                text_draw_relative_location[0] += float(ops[0])
                text_draw_relative_location[1] += float(ops[1])

            elif (instruction.operator == pikepdf.Operator("Tj")
                  or instruction.operator == pikepdf.Operator("TJ")):  # Draw text
                # For now, we just save the text start position and draw the box there
                current_section_content.append(instruction)
                if text_draw_location is None:
                    loc = (current_transformation_matrix @ current_text_matrix
                                          @ np.array([[1, 0, 0], [0, 1, 0],
                                                      [text_draw_relative_location[0],
                                                       text_draw_relative_location[1],
                                                       1.]], dtype=np.float64))
                    text_draw_location = [loc[2][0], loc[2][1]]

            elif instruction.operator == pikepdf.Operator("Tm"):
                current_section_content.append(instruction)
                ops = instruction.operands
                current_text_matrix = np.array([[float(ops[0]), float(ops[1]), .0],
                                                [float(ops[2]), float(ops[3]), .0],
                                                [float(ops[4]), float(ops[5]), 1.]], dtype=np.float64)


            elif instruction.operator == pikepdf.Operator("cm"):  # Transformation matrix command
                current_section_content.append(instruction)
                ops = instruction.operands
                current_transformation_matrix @= np.array([[float(ops[0]), float(ops[1]), .0],
                                                           [float(ops[2]), float(ops[3]), .0],
                                                           [float(ops[4]), float(ops[5]), 1.]], dtype=np.float64)

            else:
                current_section_content.append(instruction)

        if current_section_content:
            sections.append(PdfPage.Section(current_section_type, current_section_content))

        return sections

    @staticmethod
    def _join_sections(sections: List[Section]):
        instructions = []
        for s in sections:
            instructions.extend(s.content)
        return instructions

    def get_original_pike_page(self) -> pikepdf.Page:
        # if "/Contents" in self._page.keys():
        #     del self._page["/Contents"]

        self._page.mediabox = self.original_crop_area
        # self._page.contents_add(self._original_content)
        return self._page

    def get_edited_pike_page(self) -> pikepdf.Page:
        # if "/Contents" in self._page.keys():
        #     del self._page["/Contents"]

        self._page.mediabox = self.crop_area if self.crop_area else self.original_crop_area
        # self._page.contents_add(pikepdf.unparse_content_stream(self._join_sections(self.sections)))
        return self._page

    def get_boxes(self) -> List[Box]:
        boxes = []
        for section in self.sections:
            if section.typ == PdfPage.Section.SectionType.TEXT:
                box = section.get_bounding_box(page_height=float(self._page.mediabox[3]))
                if box:
                    boxes.append(box)
        return boxes

    @staticmethod
    def render_page_as_image(page: pikepdf.Page) -> Image:
        pdf_stream = io.BytesIO()
        pdf = pikepdf.Pdf.new()
        pdf.pages.append(page)
        pdf.save(pdf_stream)

        ftz = fitz.open(stream=pdf_stream)
        page = ftz.load_page(0)
        ix = page.get_pixmap()
        imgdata = ix.tobytes("ppm")

        img = Image.open(io.BytesIO(imgdata))
        return img

    def get_original_rendered_image(self):
        return self._original_rendered

    def get_edited_rendered_image(self):
        return self.render_page_as_image(self.get_edited_pike_page())


class PdfFile:
    def __init__(self, pdf: pikepdf.Pdf, path: str = None, progressbar: bool = False):
        self.path = path
        self.pdf = pdf

        if progressbar:
            from src.pdf2reader.gui.progress_bar_window import ProgressBarWindow
            progress_bar_window = ProgressBarWindow("Loading PDF", f"Loading PDF...", 0, len(self.pdf.pages))

        self.pages_parsed = []
        for page in self.pdf.pages:
            self.pages_parsed.append(PdfPage(page))
            if progressbar:
                progress_bar_window.update_progress(len(self.pages_parsed))
                progress_bar_window.update_message(f"Loading PDF... page {len(self.pages_parsed)}/{len(self.pdf.pages)}")

        if progressbar:
            progress_bar_window.close()


    @staticmethod
    def open(path: str, progressbar: bool = False) -> "PdfFile":
        pdf = pikepdf.open(path)
        pdf_file = PdfFile(pdf, path, progressbar=progressbar)
        return pdf_file

    @property
    def page_count(self) -> int:
        return len(self.pdf.pages)

    def get_page(self, page_number: int) -> PdfPage:
        return self.pages_parsed[page_number]

    def get_pike_page(self, page_number: int) -> pikepdf.Page:
        return self.pages_parsed[page_number].get_original_pike_page()

    def get_boxes(self, page_number: int) -> List[Box]:
        return [box for box in self.pages_parsed[page_number].get_boxes() if box is not None]

    def save(self, path: str, progressbar: bool = False):
        if progressbar:
            from src.pdf2reader.gui.progress_bar_window import ProgressBarWindow
            progress_bar_window = ProgressBarWindow("Saving PDF", f"Saving PDF...", 0, len(self.pages_parsed))

        for i, page in enumerate(self.pages_parsed):
            page.get_edited_pike_page()  # Just so that page data is updated before saving

            if progressbar:
                progress_bar_window.update_progress(i + 1)
                progress_bar_window.update_message(f"Saving PDF... page {i + 1}/{len(self.pages_parsed)}")

        if progressbar:
            progress_bar_window.close()

        self.pdf.save(path)
