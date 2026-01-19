import os
import pytest

from pathlib import Path
from shutil import rmtree
from skimage.metrics import structural_similarity


@pytest.mark.parametrize(
    "form_identifier, status",
    [
        ("Dummy", True),
        # ("Cat", False),
    ],
)
def test_end2end(form_identifier, status):
    from .form_tools.form_operators import FormOperator
    from .form_tools.utils.image_reader import ImageReader
    from .form_tools.form_meta.extractors.pdf_form_extractor import PdfFormMetaExtractor

    test_paths = {
        "template_images": "tests/tests_end2end/data/template_images",
        "metadata": "tests/tests_end2end/data/metadata/",
        "pass_directory": "tests/tests_end2end/data/pass_directory",
        "fail_directory": "tests/tests_end2end/data/fail_directory",
    }

    # Instantiate extractor
    pfme = PdfFormMetaExtractor()

    # Create FormMetadata object and populate
    # image directory template_images
    form_metadata = pfme.extract_meta(
        form_template_path="tests/tests_end2end/data/dummy_form.pdf",
        form_image_dir=test_paths["template_images"],
        form_image_dir_overwrite=True,
    )

    new_name_map = {
        "textbox1": "name",
        "textbox2": "occupation",
        "textbox22": "favouritelibrary",
    }

    for k, v in new_name_map.items():
        new_field = form_metadata.form_field(k)
        new_field.name = v

        # Note: we need to use update_column and remove_column
        # as form_field is only a read method. `FormMetadata` is
        # a child class of the mojap `Metadata` class and uses its
        # methods to set / update properties
        form_metadata.update_column(new_field.to_dict())
        form_metadata.remove_column(k)

    # Set form page identifiers
    identifier_map = {1: form_identifier}

    new_form_pages = []
    for pn, id in identifier_map.items():
        form_page = form_metadata.form_page(pn)
        form_page.identifier = id
        new_form_pages.append(form_page)

    form_metadata.form_pages = new_form_pages
    form_metadata.form_identifier = form_identifier

    metadata_path = Path(test_paths["metadata"])
    if not metadata_path.exists():
        metadata_path.mkdir(parents=True, exist_ok=True)

    form_metadata.to_json(
        os.path.join(test_paths["metadata"], "dummy_form_meta.json"),
        indent=4,
    )

    form_operator = FormOperator.create_from_config(
        "tests/tests_end2end/data/config.yaml"
    )

    _ = form_operator.run_full_pipeline(
        form_path="tests/tests_end2end/data/scanned_dummy_form.jpg",
        pass_dir=test_paths["pass_directory"],
        fail_dir=test_paths["fail_directory"],
        form_meta_directory="tests/tests_end2end/data/metadata",
    )

    if status:
        assert os.listdir(test_paths["pass_directory"])
        assert not os.path.exists(test_paths["fail_directory"])

        generated_image_paths = [
            p.as_posix() for p in Path(test_paths["pass_directory"]).glob("**/*.jpg")
        ]

        for form_field in form_metadata.form_fields:
            _, expected_imgs = ImageReader.read(
                f"tests/tests_end2end/data/thumbnails/{form_field.name}.jpg"
            )
            generated_field_image_path = [
                p for p in generated_image_paths if form_field.name + "/" in p
            ][0]
            _, generated_imgs = ImageReader.read(generated_field_image_path)

            assert (
                round(
                    structural_similarity(
                        generated_imgs[0],
                        expected_imgs[0],
                        win_size=3,
                    ),
                    2,
                )
                >= 0.99
            )

    else:
        assert not os.path.exists("tests/tests_end2end/data/pass_directory/")
        assert os.listdir("tests/tests_end2end/data/fail_directory/")

    for _, path in test_paths.items():
        if os.path.exists(path):
            rmtree(path)
