import os
import re
import cv2
import numpy as np

from pathlib import Path
from shutil import rmtree
from itertools import chain
from math import floor, ceil
from charset_normalizer import detect
from tempfile import TemporaryDirectory
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdftypes import resolve1, PDFObjRef
from typing import List, Dict, Tuple, Optional, Union

from ..form_meta import FormMetadata
from ..bounding_box import BoundingBox
from ...utils.image_reader import ImageReader


class PdfFormMetaExtractor:
    """PDF form metadata extractor class

    Class for extracting `FormMetadata` from a PDF form. Note,
    the PDF needs to be an enriched PDF template for this class
    to work i.e. it cannot process image files stored as PDFs.

    Attributes:
        pdf_to_image_options (Dict[str, Any]):
            Arguments to pass to `ImageReader.convert_from_path`.
    """

    def __init__(
        self,
        form_image_directory: Optional[Union[str, None]] = None,
        **pdf_to_image_options,
    ):
        if "output_folder" in pdf_to_image_options:
            raise KeyError("output_folder should not be listed in pdf2image options.")
        self.pdf_to_image_options = pdf_to_image_options
        self._form_image_directory = form_image_directory
        self._form_image_directory_populated = False

    def _make_form_image_directory(self, overwrite: Optional[bool] = False) -> None:
        """Creates directory to store the PDF images (1 per page)

        Creates a form image directory to store converted PDF page
        images that align to what the final metadata will expect
        (i.e. so that bounding box regions can be extracted)

        Params:
            overwrite (Optional[bool]): Allow overwrite of
                existing directory

        Returns:
            (None): `ValueError` raised if `_form_image_directory`
                is not set
        """
        if self._form_image_directory is not None:
            form_image_dir_path = Path(self._form_image_directory).absolute()
            if overwrite and form_image_dir_path.exists():
                _ = rmtree(form_image_dir_path.as_posix())

            _ = form_image_dir_path.mkdir(parents=True, exist_ok=True)
        else:
            raise ValueError("No form_image_directory has been specified")

    @classmethod
    def _get_pdf_pages(
        cls,
        kids: List[Dict],
        no_pages: int,
    ) -> List:
        """Helper method to retrieve PDF pages

        Retrieves all 'Kid' elements from a `pdfminer`
        tree.

        Params:
            kids (List[Dict]): Initial kids to start with

        Returns:
            (List): List of PDF page kid elements
        """
        no_kids = len(kids)
        if no_kids != no_pages:
            new_kids = list(
                chain.from_iterable([resolve1(kid)["Kids"] for kid in kids])
            )
            final_kids = cls._get_pdf_pages(new_kids, no_pages)
        else:
            final_kids = kids
        return final_kids

    @classmethod
    def _convert_rect_to_bbox(
        cls,
        field: Dict,
        pages: List,
        image_page_sizes: List[Tuple[int, int]],
    ) -> BoundingBox:
        """Helper method for converting PDF rectangles

        Fetches coordinates for a rectangle, scales to the
        overall image page size, and then converts to a
        `BoundingBox`.

        Params:
            field (Dict): PDF form field element
            pages (List): PDF pages list
            image_page_sizes (List[Tuple[int, int]]):
                List of page sizes of the converted PDF
                page image

        Returns:
            (BoundingBox): The equivalent `BoundingBox`
                object for the field rectangle
        """
        if field.get("Rect") is None:
            if len(field.get("Kids")) != 1:
                raise RuntimeError("Field has too many kids")

            kid_field = resolve1(field.get("Kids")[0])
            rect = kid_field.get("Rect")

        else:
            rect = field.get("Rect")

        x1, y1, x2, y2 = tuple(rect)
        page_number = cls._match_field_to_page(field, pages)
        page = resolve1(pages[page_number - 1])
        _, _, wp, hp = tuple(page["MediaBox"])
        wi, hi = image_page_sizes[page_number - 1]
        rh = hi / hp
        rw = wi / wp

        nx = floor(rw * x1)
        ny = floor(rh * (hp - y2))
        nw = ceil(rw * (x2 - x1))
        nh = ceil(rh * (y2 - y1))

        return BoundingBox.from_tuple((nx, ny, nw, nh))

    @staticmethod
    def _clean_field_name(
        field: Dict,
    ) -> str:
        """Helper method for cleaning field names

        Removes encoding characters from a field
        name.

        Params:
            field (Dict): PDF form field element

        Returns:
            (str): The cleaned field name
        """
        field_names = [field.get(name, b"") for name in ["TU", "T"]]
        encodings = [detect(field_name)["encoding"] for field_name in field_names]

        pattern = re.compile(r"[\W_]+")

        cleaned_fieldnames = [
            pattern.sub("", f.decode(e).lower())
            for f, e in zip(field_names, encodings)
            if f.decode(e).lower() != ""
        ]

        return "_".join(cleaned_fieldnames)

    @staticmethod
    def _match_field_to_page(
        field: Dict,
        pages: List,
    ) -> int:
        """Helper method finding a field's page

        Retrieves the page number the field is contained
        in.

        Params:
            field (Dict): PDF form field element

        Returns:
            (str): The cleaned field name
        """
        page_number = [
            i + 1 for i, page in enumerate(pages) if page.objid == field["P"].objid
        ][0]
        return page_number

    @staticmethod
    def _get_page_number_from_image_path(img_path: str) -> int:
        """Helper page number method

        Extracts a PDF page number from the converted
        PDF page image filepath

        Params:
            img_path (str): PDF page image filepath

        Returns:
            (int): The page number
        """
        suffix = Path(img_path).suffix
        match = re.search(f"[0-9]+\\{suffix}$", img_path)
        if match is not None:
            pn = int(match.group(0).replace(suffix, ""))
        else:
            raise ValueError("Image path not in the expected format")
        return pn

    @classmethod
    def _clean_form_image_directory(
        cls,
        form_img_dir: str,
        pages_to_keep: Optional[Union[List[int], None]] = None,
    ):
        """Helper method for renaming page images

        Renames page image filenames to the format
        `page_{page_number}`. If the extractor is only
        processing a subset of the PDF, then the page number
        will correspond to the numbering in the subsetted
        form i.e. if keeping pages [2, 5, 7] then these will be
        renumbered [1, 2, 3].

        Params:
            form_img_dir (str): Path to form image directory
            pages_to_keep (Optional[Union[List[int], None]]):
                Subset of pages from the form to keep

        Returns:
            (int): The page number
        """
        form_img_files = sorted(
            os.listdir(form_img_dir),
            key=lambda x: cls._get_page_number_from_image_path(x),
        )

        form_img_paths = [
            Path(os.path.join(form_img_dir, path)) for path in form_img_files
        ]

        if pages_to_keep is None:
            new_paths = [
                p.rename(os.path.join(p.parent, f"page_{i + 1}{p.suffix}"))
                for i, p in enumerate(form_img_paths)
            ]
        else:
            new_paths = []
            for i, p in enumerate(form_img_paths):
                if i + 1 in pages_to_keep:
                    new_index = pages_to_keep.index(i + 1) + 1
                    new_path = p.rename(
                        os.path.join(p.parent, f"page_{new_index}{p.suffix}")
                    )
                    new_paths.append(new_path)
                else:
                    p.unlink()

        return new_paths

    def _convert_pdf_form_to_image_dir(
        self,
        form_template_path: str,
        return_images: Optional[bool] = False,
        overwrite: Optional[bool] = False,
        pages_to_keep: Optional[Union[List[int], None]] = None,
    ) -> Union[List[np.ndarray], None]:
        """Helper creating a PDF image directory

        Takes a PDF form and creates a directory with
        an image per page in the form. This method can also
        treat a subset of a form as a complete form by passing
        a list of `pages_to_keep`.

        Params:
            form_template_path(str): Path to form image directory
            return_images (Optional[bool]): Set to `True` to
                return a list of the processed images
            overwrite (Optional[bool]):
                Set to `True` to overwrite the image directory
                if it already exists
            pages_to_keep (Optional[Union[List[int], None]]):
                Subset of pages from the form to keep

        Returns:
            Union[List[np.ndarray], None]: The list of
                processed page images if `return_images=True`
        """
        form_img_dir = self._form_image_directory
        if form_img_dir is None:
            tmp_dir = TemporaryDirectory()
            form_img_dir = tmp_dir.name
        else:
            self._make_form_image_directory(overwrite=overwrite)

        _ = ImageReader.convert_from_path(
            form_template_path, output_folder=form_img_dir, **self.pdf_to_image_options
        )
        if self._form_image_directory is not None:
            self._form_image_directory_populated = True

        new_paths = self._clean_form_image_directory(form_img_dir, pages_to_keep)

        if return_images:
            form_imgs = [cv2.imread(p.as_posix()) for p in new_paths]
        else:
            form_imgs = None

        return form_imgs

    def _get_field_meta_from_pdf(
        self,
        form_template_path: str,
        pages_to_keep: Optional[Union[List[int], None]] = None,
        overwrite: Optional[bool] = False,
    ) -> List[Dict]:
        """Helper function that creates a list of PDF form fields

        Takes a PDF form and creates a directory with
        and extracts the list of fields in the form and returns as
        a list of `FormField` compatible dictionaries.

        Params:
            form_template_path(str): Path to form image directory
            overwrite (Optional[bool]):
                Set to `True` to overwrite the image directory
                if it already exists
            pages_to_keep (Optional[Union[List[int], None]]):
                Subset of pages from the form to keep

        Returns:
            List[Dict]: A list of form fields compatible
                with the `FormField` class
        """
        path = Path(form_template_path)
        fp = open(path, "rb")

        parser = PDFParser(fp)
        doc = PDFDocument(parser)

        fields_init = resolve1(doc.catalog["AcroForm"])["Fields"]
        fields = (
            resolve1(fields_init) if isinstance(fields_init, PDFObjRef) else fields_init
        )
        pages_info = resolve1(doc.catalog["Pages"])
        kids = pages_info.get("Kids")
        count = pages_info.get("Count")

        pages = self._get_pdf_pages(kids, count)
        init_page_fields = [
            resolve1(field) for field in fields if resolve1(field).get("P")
        ]

        field_cols = [
            {
                "name": self._clean_field_name(field),
                "page_number": self._match_field_to_page(field, pages),
                "field": field,
            }
            for field in init_page_fields
        ]

        field_cols = sorted(field_cols, key=lambda x: x["page_number"])

        form_page_imgs = self._convert_pdf_form_to_image_dir(
            form_template_path=form_template_path,
            return_images=True,
            overwrite=overwrite,
            pages_to_keep=pages_to_keep,
        )

        page_imgs_shape = [img.shape for img in form_page_imgs]
        page_sizes = [(w, h) for h, w, _ in page_imgs_shape]

        if pages_to_keep is None:
            pages_to_keep = sorted(set([f["page_number"] for f in field_cols]))
            if self._form_image_directory_populated:
                _ = self._clean_form_image_directory(
                    self._form_image_directory, pages_to_keep
                )

        pages_to_keep = sorted(pages_to_keep)
        pages_list = [p for i, p in enumerate(pages) if i + 1 in pages_to_keep]

        final_field_cols = []
        for field in field_cols:
            fp_no = field["page_number"]
            if fp_no in pages_to_keep:
                page_index = pages_to_keep.index(fp_no)
                field["page_number"] = page_index + 1
                field["bounding_box"] = self._convert_rect_to_bbox(
                    field["field"], pages_list, page_sizes
                ).to_dict("ltwh")
                field.pop("field")
                final_field_cols.append(field)

        return final_field_cols

    def extract_meta(
        self,
        form_template_path: str,
        pages_to_keep: Optional[Union[List[int], None]] = None,
        form_image_dir: Optional[Union[str, None]] = None,
        form_image_dir_overwrite: Optional[bool] = False,
    ) -> FormMetadata:
        """Extracts `FormMetadata` from a PDF form

        Takes a PDF form and populates a `FormMetadata`
        object with the list of fields and pages in the form,
        along with bounding boxes for each field. Also creates
        a directory with a `FormMetadata` compatible set of images
        per page of the form.

        Params:
            form_template_path (str): Path to form image directory
            form_image_dir (Optional[Union[str, None]]): Directory
                to store the PDF page images
            form_image_dir_overwrite (Optional[bool]):
                Set to `True` to overwrite the image directory
                if it already exists
            pages_to_keep (Optional[Union[List[int], None]]):
                Subset of pages from the form to keep

        Returns:
            FormMetadata: A base `FormMetadata` object for
                the PDF form
        """
        fm = FormMetadata()

        if form_image_dir is not None:
            self._form_image_directory = form_image_dir
            self._form_image_directory_populated = False
            fm.form_template = form_image_dir
        elif self._form_image_directory is not None:
            fm.form_template = self._form_image_directory

        pdf_field_meta = self._get_field_meta_from_pdf(
            form_template_path=form_template_path,
            pages_to_keep=pages_to_keep,
            overwrite=form_image_dir_overwrite,
        )

        form_page_numbers = []
        form_pages = []

        for c in pdf_field_meta:
            fp = c["page_number"]
            c["type"] = "string"

            if fp not in form_page_numbers:
                form_pages.append(
                    {
                        "page_number": fp,
                        "identifier": "",
                        "required": True,
                        "duplicates": False,
                    }
                )

            form_page_numbers.append(fp)

        fm.columns = pdf_field_meta
        fm.form_pages = form_pages
        fm.form_formats = ["pdf"]
        fm.name = Path(form_template_path).name.lower()

        return fm
