import os
import cv2
import numpy as np

from pathlib import Path
from tempfile import TemporaryDirectory


class TestPdfFormMetaExtractor:
    TEST_PDF_FORM = "tests/tests_meta/data/forms/test_form.pdf"
    EXPECTED_FIELDS = ["myfield", "myotherfield", "mysecondpagefield"]

    def setup_test(self):
        from .form_tools.form_meta.extractors.pdf_form_extractor import (
            PdfFormMetaExtractor,
        )

        pdf_extractor = PdfFormMetaExtractor()
        return pdf_extractor

    def test_extract_meta(self):
        form_dir = Path(self.TEST_PDF_FORM).parent

        with TemporaryDirectory() as tmpdir:
            pdf_extractor = self.setup_test()
            form_meta = pdf_extractor.extract_meta(
                self.TEST_PDF_FORM, form_image_dir=tmpdir, form_image_dir_overwrite=True
            )

            field_names = []
            for field in form_meta.form_fields:
                field_name = field.name
                field_bounding_box = field.bounding_box
                field_page_number = field.page_number

                page_image = cv2.imread(
                    os.path.join(tmpdir, f"page_{field_page_number}.ppm")
                )

                l, t, w, h = field_bounding_box.to_tuple("ltwh")
                field_image = page_image[t : t + h, l : l + w]

                expected_image = cv2.imread(os.path.join(form_dir, f"{field_name}.ppm"))
                assert np.array_equal(field_image, expected_image)

                field_names.append(field_name)

            assert field_names == self.EXPECTED_FIELDS
