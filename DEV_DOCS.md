# pdf2reader dev documentation

Pdf2reader GUI is built with default pythons tkinter toolkit.  
PDF backend is mostly built on top of the `pikepdf` bindings for `qpdf` C library.  
Application entry point is the main() function inside `__main.py__` file.

## Working with PDF

Most of working with PDFs is done in the `pdf_file.py` file. 
`PdfFile` is the main class that holds a open PDF file.  

### Opening PDF pipeline

- Parse all pages into `PdfPage` object
- Match text section between pages
- Extract images from pdf to temporary folder

### Parsing PDF page

Parsing happens inside `PdfPage._parse_sections` function.  
PDF page is parsed into list of `Section` objects of type either `text` or `other`. 
`text` section is a section between `BT` and `ET` tags in PDF. 
These `text` section are the ones we are matching between pages so they can be removed by user. 

### How are text Sections compared for similarity

Comparison for similarity is done in the `PdfFile._get_section_similarity` and can be 
influenced by setting `self.max_absolute_location_diff` and `self.max_relative_font_size_diff`  

**Similarity is checked based on:**
- Font
- Font size
- Location
- Content

### Images optimization

Images optimization heavy lifting is handled in `images_optimization.py`

When opening PDF file, all images that are optimizable are exported to a temporary folder. 
This is to ensure that images optimizations are not cumulative, but always it optimizes the
original image.

## GUI

All the GUI stuff is in the `gui` folder. Main window creation is in the `__main__.py` file.  
GUI is mostly build around opening new windows for each thing user wants to do.    


### `MainGUI`

Handling main app view and menu buttons.

### `PdfPageGridDisplay`

Handles displaying grid of PDF pages. Can be embedded into multiple places.

### `PageRenderer`

Handles rendering single PDF page.  
Handles rendering boxes around text and delegating on click events to the right box.

### `PageEditWindow`

Manages cropping for page using `CropSelector` and opening batch crop selector.  
Handles text boxes to be marked for removal and opening batch removal selector.

### `SelectPagesToActionWindow`

Handles smart selecting multiple from a grid.  
Highly configurable.
