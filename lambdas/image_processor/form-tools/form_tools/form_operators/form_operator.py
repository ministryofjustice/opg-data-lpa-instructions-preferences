import re
import os
import cv2
import importlib
import numpy as np
import pandas as pd
import awswrangler as wr

from shutil import copy
from pathlib import Path
from logging import getLogger
from datetime import datetime
from pydantic import BaseModel
from arrow_pd_parser import writer
from tempfile import NamedTemporaryFile
from typing import Union, List, Dict, Tuple, Optional
from dataengineeringutils3.s3 import s3_path_to_bucket_key, _add_slash

from ..form_meta import FormMetadata
from .ocr_engines.base import BaseOcrEngine
from ..utils.image_reader import ImageReader
from .form_page_operator import FormPageOperator
from .operator_configs import FormOperatorConfig
from .bounding_box_operator import BoundingBoxOperator

logger = getLogger(__name__)


class FormOperator(BaseModel):
    """Operator for a form

    Applies transformations to an instance (image, image text) of
    a form. Transformations including aligning form images to a
    given template and extracting fields from a form as image
    thumbnails.

    Attributes:
        config (FormOperatorConfig): A form operator config
            for setting up image transformations
        rotation_engine (BaseOcrEngine): A OCR
            engine to use for auto-rotating form images
            based on
        text_extraction_engine (BaseOcrEngine): A OCR
            engine to use for text extraction
        form_page_operator (FormPageOperator): A
            `FormPageOperator` populated from the given
            `FormOperatorConfig` for processing individual
            form pages
    """

    config: FormOperatorConfig

    @staticmethod
    def _get_ocr_engine(engine_name: str) -> BaseOcrEngine:
        """Helper for retrieving OCR engine from name

        Takes an OCR engine name and works out the
        corresponding engine class for importing
        from `form_tools.form_operators.ocr_engines`

        Params:
            engine_name (str): The name of the OCR engine
                to fetch

        Return:
            (BaseOcrEngine):
                The given engine's class
        """
        engine_class_name = engine_name[0].upper() + engine_name[1:] + "OcrEngine"
        module = importlib.import_module(
            f"form_tools.form_operators.ocr_engines.{engine_name.lower()}"
        )
        engine = getattr(module, engine_class_name)
        return engine

    @property
    def rotation_engine(self) -> BaseOcrEngine:
        engine = self._get_ocr_engine(self.config.ocr_options.rotation_engine)
        return engine(**self.config.ocr_options.dict())

    @property
    def text_extractrion_engine(self) -> BaseOcrEngine:
        engine = self._get_ocr_engine(self.config.ocr_options.text_extraction_engine)
        return engine(**self.config.ocr_options.dict())

    @property
    def form_page_operator(self) -> FormPageOperator:
        return FormPageOperator.create_from_config(self.config)

    @classmethod
    def create_from_config(
        cls,
        config: Union[str, dict, FormOperatorConfig],
    ):
        """Creates a `FormOperator` from a config

        Takes a `FormOperatorConfig` to create an
        instance of a `FormOperator`. Config
        can be provided as a path to a valid config
        yaml file, a yaml string, dictionary or
        `FormOperatorConfig` object.

        Params:
            config (Union[str, dict, FormOperatorConfig]):
                An object pointing to or representing
                a valid `FormOperatorConfig`

        Returns:
            (FormPageOperator): An instantiated
                `FormPageOperator` object with
                the given config
        """
        if isinstance(config, FormOperatorConfig):
            operator = cls(config=config)

        elif isinstance(config, dict):
            operator_config = FormOperatorConfig(**config)
            operator = cls(config=operator_config)

        else:
            config = FormPageOperator._read_config(config)
            operator = cls(config=config)

        return operator

    @staticmethod
    def form_meta_store(form_meta_directory: str) -> Dict[str, FormMetadata]:
        """Returns form metadata files in directory

        Returns a dictionary of `FormMetadata` objects populated
        from valid json files in the given directory.

        Params:
            form_meta_directory (str):
                The local path to the directory containing
                `FormMetadata` compliant json files

        Return:
            (Dict[str, FormMetadata]):
                A dictionary of `FormMetadata` objects
        """
        return {
            p.stem: FormMetadata.from_json(p.as_posix())
            for p in Path(form_meta_directory).glob("*.json")
        }

    def match_form_images_text_to_form_meta(
        self, form_meta_directory: str, form_images_as_strings: List[str]
    ):
        """Filters form meta directory using given form image strings

        Loops through `FormMetadata` objects in a given directory
        and only returns those where the given form images
        contains the given metadata's identifier

        Params:
            form_meta_directory (str):
                The local path to the directory containing
                `FormMetadata` compliant json files
            form_images_as_strings (List[str]):
                List of recognised text from a set of form images

        Return:
            (Dict[str, FormMetadata]):
                A dictionary of `FormMetadata` objects
        """
        results = {}
        for id, meta in self.form_meta_store(form_meta_directory).items():
            valid, _ = self.form_identifier_match(form_images_as_strings, meta)
            if valid:
                results[id] = meta

        return results

    def form_images_to_text(self, images: List[np.ndarray]) -> List[str]:
        """Extracts text from given images

        Takes a list of form page images and uses
        the configured OCR engine to extract
        text from each image.

        Params:
            images (List[ndarray]):
                A list of form page images

        Return:
            (ndarray):
                A list of recognised text from
                the given images
        """
        engine = self.text_extractrion_engine
        return engine.extract_text_from_images(images)

    def form_identifier_match(
        self,
        form_images_as_strings: List[str],
        form_meta: FormMetadata,
        identifier: Optional[Union[str, None]] = None,
        excluded: Optional[Union[List[str], None]] = None,
        filter_excluded_out: Optional[bool] = True,
    ) -> Tuple[bool, List[int]]:
        """Checks if a form metadata identifier is in a form

        Takes a list of form page image text and checks
        whether the text contains the required `FormMetadata`
        objects' identifier, if none is supplied.

        Params:
            form_images_as_strings (List[str]):
                List of recognised text from a set of form images
            form_meta (FormMetadata): A `FormMetadata`
                object for comparison
            identifier (Optional[Union[List[str], None]]):
                Alternative identifier to use rather
                than the one recorded in the `FormMetadata`
                object
            excluded (Optional[Union[List[str], None]]):
                Alternative excluded sections to use rather
                than those recorded in the `FormMetadata`
                object
            filter_excluded_out (Optional[bool]):
                Whether to filter pages matching
                excluded sections out before comparison

        Return:
            (Tuple[bool, List[int]]):
                A tuple where the first argument
                specifies whether there is a match
                and the second is the list of page
                numbers where the match occur
        """
        form_identifier = (
            form_meta.form_identifier if identifier is None else identifier
        )
        form_excluded = form_meta.excluded_sections if excluded is None else excluded

        form_match = False
        form_matches = []
        for i, img_str in enumerate(form_images_as_strings):
            id_match = re.search(form_identifier, img_str, re.DOTALL)

            if form_excluded is not None and filter_excluded_out:
                excl_match = [
                    re.search(exl, img_str, re.DOTALL) for exl in form_excluded
                ]

                excl_flag = len([e for e in excl_match if e is not None]) > 0

            else:
                excl_flag = False

            if id_match is not None and not excl_flag:
                form_match = True
                form_matches += [i]

        return form_match, form_matches

    def align_images_to_template(
        self,
        image_page_mapping: Dict[int, List[np.ndarray]],
        form_meta: FormMetadata,
        debug: Optional[bool] = False,
    ) -> Dict[int, List[np.ndarray]]:
        """Aligns form page images to a form template

        Takes a form page to form images mapping dictionary
        and a given form metadata object and uses the
        `FormOperator.form_page_operator` to align the
        given set of images to the form template images
        found in the specified directory in the given
        form metadata.

        Params:
            image_page_mapping (Dict[int, List[np.ndarray]]):
                A dictionary where keys are page numbers and
                values are lists of form page images which
                have been identified as matching that page
            form_meta (FormMetadata): A `FormMetadata`
                object for comparison
            debug (Optional[bool]):
                Whether to show image outputs using `opencv`
                during processing - will require user input
                to continue

        Return:
            Dict[int, List[np.ndarray]]:
                A dictionary where keys are page numbers and
                values are lists of aligned form page images
        """
        fp_op = self.form_page_operator
        form_meta_loc = form_meta.form_template
        template_files = os.listdir(form_meta_loc)

        aligned_image_mapping = {}
        for pn, imgs in image_page_mapping.items():
            tpt_file = [tpg for tpg in template_files if f"_{pn}" in tpg]

            _, template_image = ImageReader.read(
                os.path.join(form_meta_loc, tpt_file[0])
            )

            if len(template_image) != 1:
                raise ValueError(
                    "Template directory should contain\n"
                    "a single image file for each page in\n"
                    "the template."
                )

            aligned_images = [
                fp_op.align_image_to_template(
                    page_image=scanned_image,
                    page_template_image=template_image[0],
                    debug=debug,
                )
                for scanned_image in imgs
            ]

            aligned_image_mapping[pn] = aligned_images

        return aligned_image_mapping

    def extract_fields(
        self,
        image_page_mapping: Dict[str, List[np.ndarray]],
        form_meta: FormMetadata,
        as_bytes: Optional[bool] = False,
        encode_type: Optional[str] = ".jpg",
        debug: Optional[bool] = False,
    ) -> Dict[str, Union[List[np.ndarray], np.ndarray]]:
        """Extracts fields from form page images

        Takes a form page to form images mapping dictionary
        and extracts fields from the images using the bounding
        boxes given in the form metadata

        Params:
            image_page_mapping (Dict[int, List[np.ndarray]]):
                A dictionary where keys are page numbers and
                values are lists of form page images which
                have been identified as matching that page
            form_meta (FormMetadata): A `FormMetadata`
                object for comparison
            as_bytes (Optional[bool]):
                Whether to return images as byte strings
            encode_type (Optional[str]):
                If `as_bytes=True`, the image file format
                for encoding during conversion to bytes
            debug (Optional[bool]):
                Whether to show image outputs using `opencv`
                during processing - will require user input
                to continue

        Return:
            Dict[str, Union[List[np.ndarray], np.ndarray]]:
                A dictionary where keys are field names and
                values are image(s) corresponding to the form
                field
        """
        form_fields = form_meta.form_fields
        bb_op = BoundingBoxOperator()

        field_img_dict = {}
        for field in form_fields:
            field_pn = field.page_number
            field_page = form_meta.form_page(field_pn)
            field_has_duplicate = field_page.duplicates
            aligned_images = image_page_mapping[field_pn]
            field_bb = field.bounding_box

            field_img = [
                bb_op.crop_image_to_bb(img, bounding_box=field_bb)
                for img in aligned_images
            ]

            if as_bytes:
                field_img = [
                    cv2.imencode(encode_type, img)[1].tobytes() for img in field_img
                ]

            if debug:
                for img in field_img:
                    cv2.imshow(field.name, img)
                    cv2.waitKey(0)

            field_img_dict[field.name] = (
                field_img if field_has_duplicate else field_img[0]
            )

        return field_img_dict

    @staticmethod
    def _copy_to_fail(form_path: str, fail_dir: str, meta_id: str, timestamp: int):
        """Helper method for copying failed forms to a fail directory

        Copies a given form from it's local / S3 location to
        a given fail directory (either locally or in S3).
        Failed copies will be partitioned by the given meta id
        and timestamp

        Params:
            form_path (str):
                Local or S3 path to form
            fail_dir (str):
                Local or S3 path to fail directory
            meta_id (str):
                The id for the form metadata where the form
                has failed to be processed against
            timestamp (int):
                The timestamp for the process run
        """
        full_fail_dir = os.path.join(fail_dir, f"meta={meta_id}", f"run={timestamp}")

        full_fail_path = os.path.join(full_fail_dir, Path(form_path).name)

        if full_fail_path.startswith("s3://") and form_path.startswith("s3://"):
            b, k = s3_path_to_bucket_key(form_path)
            source_path = os.path.join(f"s3://{b}", Path(k).parent)

            wr.s3.copy_objects(
                [full_fail_path],
                source_path=_add_slash(source_path),
                target_path=_add_slash(full_fail_dir),
            )

        else:
            _ = Path(full_fail_dir).mkdir(parents=True, exist_ok=False)
            if form_path.startswith("s3://"):
                _ = wr.s3.download(form_path, local_file=full_fail_path)
            else:
                _ = copy(form_path, full_fail_path)

    @staticmethod
    def _write_to_pass(
        extracted_fields: Dict[str, Union[List[np.ndarray], np.ndarray]],
        original_path: str,
        pass_dir: str,
        meta_id: str,
        timestamp: int,
        as_bytes: Optional[bool] = False,
        encode_type: Optional[str] = ".jpg",
    ):
        """Helper method for writing out processing outputs

        Writes extracted fields to a pass directory either
        locally or in S3.

        Params:
            extracted_fields (Dict[str, Union[List[ndarray], ndarray]]):
                A dictionary where keys are field names and
                values are image(s) corresponding to the form
                field
            original_path (str):
                Local or S3 path to original form
            pass_dir (str):
                Local or S3 path to pass directory
            meta_id (str):
                The id for the form metadata where the form
                has failed to be processed against
            timestamp (int):
                The timestamp for the process run
            as_bytes: Optional[bool] = False
                Whether data has been converted to
                bytes and needs writing out to a parquet
                dataset
            encode_type (Optional[str]):
                The file format for outputting field images
        """
        output_extension = ".snappy.parquet" if as_bytes else encode_type

        full_pass_dir = os.path.join(
            pass_dir,
            f"run={timestamp}",
            f"meta={meta_id}",
        )

        if as_bytes:
            full_pass_path = os.path.join(
                full_pass_dir, f"{Path(original_path).stem}{output_extension}"
            )
            fields_df = pd.DataFrame(extracted_fields, index=[0])

            _ = writer.write(fields_df, output_path=full_pass_path)

        else:
            for field, imgs in extracted_fields.items():
                if not isinstance(imgs, list):
                    imgs = [imgs]

                for i, img in enumerate(imgs):
                    full_pass_path = os.path.join(
                        full_pass_dir,
                        f"field_name={field}",
                        f"{i:02d}_{Path(original_path).stem}{output_extension}",
                    )

                    if full_pass_path.startswith("s3://"):
                        with NamedTemporaryFile(suffix=output_extension) as tmp:
                            _ = cv2.imwrite(tmp.name, img)
                            _ = wr.s3.upload(tmp.name, full_pass_path)
                    else:
                        _ = Path(full_pass_path).parent.mkdir(
                            parents=True, exist_ok=False
                        )
                        _ = cv2.imwrite(full_pass_path, img)
