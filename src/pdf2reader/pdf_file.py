import io
import logging
from difflib import SequenceMatcher
from enum import Enum
from tempfile import TemporaryDirectory
from typing import List

import fitz
import numpy as np
import pikepdf
from PIL import Image

from pdf2reader.data_structures import Box
from pdf2reader.images_optimization import optimize_pdf_images, OptimizationOptions, extract_pdf_images

logger = logging.getLogger(__name__)


class Section:
    # Section information
    typ: "SectionType"
    content: List[pikepdf.ContentStreamInstruction]
    location: List[float] or None
    additional: dict or None
    page_number: int or None

    # Section output options
    keep_in_output: bool
    section_group: "SectionGroup" or None

    class SectionType(Enum):
        TEXT = "text"
        OTHER = "other"
        OBJECT = "object"

    def __init__(self, typ: SectionType, content: List[pikepdf.ContentStreamInstruction], page_number: int = None,
                 location: List[float] = None, additional: dict = None, keep_in_output: bool = True):
        self.typ = typ
        self.content = content
        self.location = location
        self.additional = additional
        self.page_number = page_number

        self.keep_in_output = keep_in_output
        self.section_group = None


    def get_bounding_box(self, page_height: float, cap_area: List[int] = None) -> Box or None:
        if self.typ == Section.SectionType.TEXT:
            if self.location is None:
                logger.warning("WARNING: Text section has no location!")
                return None
            loc = [self.location[0] - 5,
                    page_height - self.location[1],
                    self.location[0] + self.additional["font_size"] * 1.2 + 5,
                    page_height - self.location[1] - self.additional["font_size"] * 1.2 + 5]
            loc[0] = min(max(loc[0], 0), cap_area[2] - 30)  # x1
            loc[1] = min(max(loc[1], 0), cap_area[3] - 15)  # y1
            loc[2] = max(min(loc[2], cap_area[2]), 15)      # x2
            loc[3] = max(min(loc[3], cap_area[3]), 20)      # y2
            return Box(*loc,
                       color="lightgreen" if self.keep_in_output else "red",
                       on_click=lambda *args, **kwargs: None)

        elif self.typ == Section.SectionType.OBJECT:
            if self.location is None:
                logger.warning("WARNING: Object section has no location!")
                return None
            loc = [self.location[0] - 20, page_height - self.location[1] - 20,
                       self.location[0] + 30, page_height - self.location[1] + 30]
            loc[0] = min(max(loc[0], 0), cap_area[2] - 20)  # x1
            loc[1] = min(max(loc[1], 0), cap_area[3] - 30)  # y1
            loc[2] = max(min(loc[2], cap_area[2]), 20)      # x2
            loc[3] = max(min(loc[3], cap_area[3]), 30)      # y2
            return Box(*loc,
                       color="lightgreen" if self.keep_in_output else "red",
                       on_click=lambda *args, **kwargs: None)


    def get_content_as_string(self):
        return "".join([str(x) for x in self.content])

    def __repr__(self):
        return (f"Section(type={self.typ}, len={len(self.content)}, page={self.page_number}, "
                f"keep_in_output={self.keep_in_output}, location={self.location}, additional={self.additional})")


class SectionGroup:
    def __init__(self, master_section: "Section", last_matched_page_number: int = None):
        self.master_section = master_section
        self.last_matched_page_number = last_matched_page_number or -1
        self.sections = [master_section]


class PdfPage:
    def __init__(self, page: pikepdf.Page, page_number: int = -1):
        self._page = page
        self._parsed_stream = pikepdf.parse_content_stream(self._page)

        self._original_content = pikepdf.unparse_content_stream(self._parsed_stream)
        self._original_rendered = self.render_page_as_image(self._page)

        self.sections = self._parse_sections(pikepdf.parse_content_stream(self._page), page_number, self._page.resources)

        self.original_crop_area: List[float] = [float(self._page.mediabox[0]), float(self._page.mediabox[1]),
                                                float(self._page.mediabox[2]), float(self._page.mediabox[3])]

        self.crop_area = None

    @property
    def original_height(self) -> int:
        return int(self.original_crop_area[3] - self.original_crop_area[1])

    @property
    def original_width(self) -> int:
        return int(self.original_crop_area[2] - self.original_crop_area[0])

    @staticmethod
    def _parse_sections(parsed_stream: List[pikepdf.ContentStreamInstruction], page_number: int = None, page_resources: pikepdf.Dictionary = None) -> List[Section]:
        sections = []

        current_section_type = Section.SectionType.OTHER
        current_section_content = []

        transform_matrixes = [np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float64)]
        def get_combined_transform_matrix():
            return np.linalg.multi_dot(transform_matrixes) if len(transform_matrixes) >= 2 else transform_matrixes[0]
        current_text_matrix = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float64)
        current_font = ("default_font", 11)  # Some random default value  (name, size)
        text_draw_relative_location = [0, 0]
        text_draw_location = None
        text = []

        for instruction in parsed_stream:
            if instruction.operator == pikepdf.Operator("BT"):  # Begin text section
                if current_section_content:
                    sections.append(Section(current_section_type, current_section_content, page_number))

                if current_section_type == Section.SectionType.TEXT:
                    logger.warning("WARNING: text_section already started!")

                current_section_content = [instruction]
                current_section_type = Section.SectionType.TEXT
                current_text_matrix = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float64)
                text_draw_relative_location = [0, 0]
                text_draw_location = None
                text = []

            elif instruction.operator == pikepdf.Operator("ET"):  # End text section
                current_section_content.append(instruction)

                if current_section_type != Section.SectionType.TEXT:
                    logger.warning("WARNING: text_section not started, but now ending!")

                if text_draw_location:
                    sections.append(Section(Section.SectionType.TEXT, current_section_content, page_number,
                                            text_draw_location,
                                            {"font": current_font[0], "font_size": current_font[1], "text": text}))
                text_draw_location = None
                current_section_content = []
                current_section_type = Section.SectionType.OTHER

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
                loc = (get_combined_transform_matrix() @ current_text_matrix
                       @ np.array([[1, 0, 0], [0, 1, 0],
                                   [text_draw_relative_location[0],
                                    text_draw_relative_location[1],
                                    1.]], dtype=np.float64))
                if text_draw_location is None:
                    text_draw_location = [loc[2][0], loc[2][1]]

                # Append text to section text
                text.append({"content": instruction.operands[0], "location": [loc[2][0], loc[2][1]],
                             "font": current_font[0], "font_size": current_font[1]})

            elif instruction.operator == pikepdf.Operator("Tm"):
                current_section_content.append(instruction)
                ops = instruction.operands
                current_text_matrix = np.array([[float(ops[0]), float(ops[1]), .0],
                                                [float(ops[2]), float(ops[3]), .0],
                                                [float(ops[4]), float(ops[5]), 1.]], dtype=np.float64)

            elif instruction.operator == pikepdf.Operator("cm"):  # Transformation matrix command
                current_section_content.append(instruction)
                ops = instruction.operands
                transform_matrixes[-1] = transform_matrixes[-1] \
                                                @ np.array([[float(ops[0]), float(ops[1]), .0],
                                                           [float(ops[2]), float(ops[3]), .0],
                                                           [float(ops[4]), float(ops[5]), 1.]], dtype=np.float64)

            elif instruction.operator == pikepdf.Operator("Do"):  # Draw image or other object
                # End current section
                if text_draw_location:
                    sections.append(Section(Section.SectionType.TEXT, current_section_content, page_number,
                                            text_draw_location,
                                            {"font": current_font[0], "font_size": current_font[1], "text": text}))
                    text_draw_location = None
                else:
                    sections.append(Section(Section.SectionType.OTHER, current_section_content, page_number))

                # Insert object section
                loc = np.eye(3, dtype=np.float64)
                loc = get_combined_transform_matrix() @ loc
                if current_section_type == Section.SectionType.TEXT:
                    loc = current_text_matrix @ loc

                pdf_obj = page_resources.XObject[instruction.operands[0]]
                pdf_obj_xref = pdf_obj.objgen[0]
                sections.append(Section(Section.SectionType.OBJECT, [instruction], page_number,
                                        [loc[2][0], loc[2][1]], additional={"xref": pdf_obj_xref}))

                # Keep current_section_type and other variables and start continuation of section
                current_section_content = []

            elif instruction.operator == pikepdf.Operator("q"):  # Push transformation matrix
                current_section_content.append(instruction)
                transform_matrixes.append(np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float64))

            elif instruction.operator == pikepdf.Operator("Q"):  # Pop transformation matrix
                current_section_content.append(instruction)
                transform_matrixes.pop()

            elif (instruction.operator == pikepdf.Operator("BDC")
                  or instruction.operator == pikepdf.Operator("BMC")):  # Marked section start
                current_section_content.append(instruction)
                transform_matrixes.append(np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float64))

            elif instruction.operator == pikepdf.Operator("EMC"):  # Marked section end
                current_section_content.append(instruction)
                transform_matrixes.pop()

            else:
                current_section_content.append(instruction)

        if current_section_content:
            sections.append(Section(current_section_type, current_section_content, page_number))

        return sections

    @staticmethod
    def _join_sections(sections: List[Section]):
        instructions = []
        for s in sections:
            if s.keep_in_output:
                instructions.extend(s.content)
        return instructions

    def get_original_pike_page(self) -> pikepdf.Page:
        if "/Contents" in self._page.keys():
            del self._page["/Contents"]

        self._page.mediabox = self.original_crop_area
        self._page.contents_add(self._original_content)
        return self._page

    def get_edited_pike_page(self) -> pikepdf.Page:
        if "/Contents" in self._page.keys():
            del self._page["/Contents"]

        self._page.mediabox = self.crop_area if self.crop_area else self.original_crop_area
        self._page.contents_add(pikepdf.unparse_content_stream(self._join_sections(self.sections)))
        return self._page

    def get_boxes(self) -> List[Box]:
        boxes = []
        for section in self.sections:
            if section.typ != Section.SectionType.OTHER:
                box = section.get_bounding_box(page_height=float(self.original_crop_area[3]),
                                               cap_area=self.original_crop_area)
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

    def get_original_rendered_image(self) -> Image:
        return self._original_rendered

    def get_edited_rendered_image(self):
        return self.render_page_as_image(self.get_edited_pike_page())


class PdfFile:
    def __init__(self, pdf: pikepdf.Pdf, path: str = None, progressbar: bool = False):
        self.path = path
        self.pdf = pdf

        self.temp_dir = TemporaryDirectory()

        # Matching params
        self.match_ahead_pages = 8
        self.match_threshold = 0.98

        self.max_relative_font_size_diff = 0.1
        self.max_absolute_location_diff = 20


        if progressbar:
            from .gui.progress_bar_window import ProgressBarWindow
            self.progress_bar_window = ProgressBarWindow("Loading PDF", f"Loading PDF...", 0, len(self.pdf.pages))

        self.pages_parsed = []
        for page_number, page in enumerate(self.pdf.pages):
            self.pages_parsed.append(PdfPage(page, page_number))
            if progressbar:
                self.progress_bar_window.update_progress(len(self.pages_parsed))
                self.progress_bar_window.update_message(
                    f"Loading PDF... page {len(self.pages_parsed)}/{len(self.pdf.pages)}")

        # if progressbar:
        #     self.progress_bar_window.update_message("Matching similar sections...")
        #     self.progress_bar_window.update_mode_infinite(True)
        self.sections_groups = []
        self._match_page_sections(progressbar=progressbar)

        # Extract images for further optimization
        if progressbar:
            self.progress_bar_window.update_message("Preparing images...")
            self.progress_bar_window.update_mode_infinite(True)
        self.images = extract_pdf_images(self.pdf, self.temp_dir.name)

        if progressbar:
            self.progress_bar_window.close()

    def _match_page_sections(self, progressbar: bool = False):
        if progressbar:
            self.progress_bar_window.update_message("Matching similar sections...")
            self.progress_bar_window.update_progress(0)
        for page_index in range(len(self.pages_parsed)):
            if progressbar:
                self.progress_bar_window.update_progress(page_index + 1)
                self.progress_bar_window.update_message(
                    f"Matching similar sections... page {page_index + 1}/{len(self.pages_parsed)}")
            page = self.pages_parsed[page_index]
            for section in page.sections:
                # Match only text and object sections
                if section.typ == Section.SectionType.OTHER:
                    continue

                # Create new sections group if this section is not part of any group
                if section.section_group is None:
                    group = SectionGroup(section)
                    group.last_matched_page_number = page_index
                    self.sections_groups.append(group)
                    section.section_group = group

                # Do the matching
                for next_page_index in range(max(page_index + 1, section.section_group.last_matched_page_number + 1),
                                             min(page_index + self.match_ahead_pages + 1, self.page_count)):
                    section.section_group.last_matched_page_number = max(section.section_group.last_matched_page_number,
                                                                         next_page_index)
                    next_page = self.pages_parsed[next_page_index]
                    similarities = self._get_section_to_sections_similarities(section.section_group.master_section,
                                                                                 next_page.sections)
                    if similarities:
                        most_similar = np.argmax(similarities)
                        if similarities[most_similar] > self.match_threshold:
                            next_page_section = next_page.sections[most_similar]
                            section.section_group.sections.append(next_page_section)
                            next_page_section.section_group = section.section_group

    def _filter_sections_groups(self):
        logger.debug(
            f"Filtering sections groups with min_group_size={self.min_group_size}. Total groups: {len(self.sections_groups)}")
        self.sections_groups = [group for group in self.sections_groups if len(group.sections) > self.min_group_size]
        logger.debug(f"Filtered groups. New count: {len(self.sections_groups)}")

    def _get_section_similarity(self, section1: Section, section2: Section) -> float:
        """ 0 is completely different, 1 is completely the same """
        if section1.typ != section2.typ:
            return 0

        # Non matching location -> non matching section
        location_x_diff = abs(section1.location[0] - section1.location[0])
        location_y_diff = abs(section1.location[1] - section1.location[1])
        if (location_x_diff > self.max_absolute_location_diff
                or location_y_diff > self.max_absolute_location_diff):
            return 0
        global_location_diff_similarity_modifier = 1 - (
                    (location_x_diff + location_y_diff) / (2 * self.max_absolute_location_diff))

        if section1.typ == Section.SectionType.TEXT == section2.typ:
            # section.additional["text"] = {"content", "location", "font", "font_size"}[]
            if len(section1.additional["text"]) != len(section2.additional["text"]):
                return 0

            texts_similarities = [1]
            for txt1, txt2 in zip(section1.additional["text"], section2.additional["text"]):
                # Non matching fonts -> non matching section
                if txt1["font"] != txt2["font"]:
                    return 0

                # Non matching location -> non matching section
                location_x_diff = abs(txt1["location"][0] - txt2["location"][0])
                location_y_diff = abs(txt1["location"][1] - txt2["location"][1])
                if (location_x_diff > self.max_absolute_location_diff
                        or location_y_diff > self.max_absolute_location_diff):
                    return 0
                location_diff_similarity_modifier = 1 - ((location_x_diff + location_y_diff) / (2 * self.max_absolute_location_diff))

                # Non matching font sizes -> non matching section
                font_size_norm_diff = (abs(txt1["font_size"] - txt2["font_size"]) / max(txt1["font_size"], txt2["font_size"]))
                if font_size_norm_diff > self.max_relative_font_size_diff:
                    return 0
                font_size_diff_similarity_modifier = 1 - font_size_norm_diff

                # Non matching content types -> non matching section
                if type(txt1["content"]) is not type(txt2["content"]):
                    return 0

                # Non matching content -> non matching section
                cnt1, cnt2 = txt1["content"], txt2["content"]
                similar = 0
                if isinstance(cnt1, str) and isinstance(cnt2, str):
                    similar = SequenceMatcher(None, cnt1, cnt2).quick_ratio()
                elif isinstance(cnt1, pikepdf.Array) and isinstance(cnt2, pikepdf.Array):
                    array1 = [str(x) for x in cnt1 if not isinstance(x, int) and not isinstance(x, float)]
                    array2 = [str(x) for x in cnt2 if not isinstance(x, int) and not isinstance(x, float)]
                    similar = SequenceMatcher(None, "".join(array1), "".join(array2)).quick_ratio()
                else:
                    logger.warning(f"WARNING: Unknown text content type: '{type(cnt1)}' or '{type(cnt2)}'")
                    continue  # Dont use in comparison

                texts_similarities.append(similar * font_size_diff_similarity_modifier * location_diff_similarity_modifier)

            total_similarity_score = np.prod(texts_similarities)
            return total_similarity_score

        if section1.typ == Section.SectionType.OBJECT == section2.typ:
            # Can not compare local object easily
            if not section1.additional["xref"] or not section2.additional["xref"]:
                return 0

            # Check if it is the same object by xref
            if section1.additional["xref"] != section2.additional["xref"]:
                return 0

            return global_location_diff_similarity_modifier

        return 0

    def _get_section_to_sections_similarities(self, section1: Section, sections: List[Section]) -> List[float]:
        similarities = []
        for section2 in sections:
            if section2.section_group is not None:
                similarities.append(-1)
            else:
                similarities.append(self._get_section_similarity(section1, section2))
        return similarities

    def __del__(self):
        self.temp_dir.cleanup()

    @staticmethod
    def open(path: str, progressbar: bool = False, password: str = None, ask_password: bool = False) -> "PdfFile":
        try:
            pdf = pikepdf.open(path, password=password or "")
        except pikepdf.PasswordError as e:
            if ask_password:
                import tkinter as tk
                import tkinter.simpledialog
                r = tk.Tk()
                r.withdraw()
                passwd = tkinter.simpledialog.askstring("PDF password", "PDF password: ", show='*', parent=r)
                r.destroy()
                if passwd == password:
                    raise e
                pdf = pikepdf.open(path, password=passwd or "")  # Can also raise PasswordError
            else:
                raise e

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
            from .gui.progress_bar_window import ProgressBarWindow
            progress_bar_window = ProgressBarWindow("Saving PDF", f"Saving PDF...", 0, len(self.pages_parsed))

        for i, page in enumerate(self.pages_parsed):
            page.get_edited_pike_page()  # Just so that page data is updated before saving

            if progressbar:
                progress_bar_window.update_progress(i + 1)
                progress_bar_window.update_message(f"Saving PDF... page {i + 1}/{len(self.pages_parsed)}")

        if progressbar:
            progress_bar_window.close()

        self.pdf.remove_unreferenced_resources()
        self.pdf.save(path)

    def optimize_images(self, images_quality: int = 30, should_resize_images: bool = True,
                        should_remove_images: bool = False, progressbar: bool = False):
        if progressbar:
            from .gui.progress_bar_window import ProgressBarWindow
            progress_bar_window = ProgressBarWindow("Optimizing images", f"Optimizing images...",
                                                    0, len(self.pages_parsed), infinite_mode=True)

        logger.info(f"Optimizing images with params quality={images_quality}, resize={should_resize_images}, "
                    f"remove={should_remove_images}")
        options = OptimizationOptions(
            jpg_quality=images_quality,
            png_quality=images_quality,
            should_resize=should_resize_images,
            should_remove_images=should_remove_images
        )
        optimize_pdf_images(self.pdf, self.images, self.temp_dir.name, options)

        if progressbar:
            progress_bar_window.close()
