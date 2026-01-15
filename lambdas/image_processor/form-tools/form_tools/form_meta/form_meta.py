import re

from copy import deepcopy
from warnings import warn
from pydantic import BaseModel, validator
from jsonschema.exceptions import ValidationError
from typing import List, Union, Any, Dict, Optional
from mojap_metadata.metadata.metadata import (
    MetadataProperty,
    Metadata,
)

from .form_field import FormField
from .bounding_box import BoundingBox


class FormPage(BaseModel):
    """Form page class.

    Represents a page in a form template, typically a PDF
    form. Each page has a regular expression identifier
    where a page in the form template is an instance of a
    given `FormPage` if the text in the page matches the given regular
    expression.

    Attributes:
        identifier (str): Regex identifier for the page
        page_number (int): Page number for the page in the template
            folder
        required (Optional[Union[bool, None]]): Whether the page is
            required to be present in an instance of a document to
            class as a valid form
        duplicates (Optional[Union[bool, None]]): Whether duplicates
            of the given page are allowed in the form document
        additional_args (Optional[Union[Dict[str, Any], None]]):
            Any additional arguments related to the page
        form_meta (Optional[Union[FormMetadata, None]]):
            The FormMetadata that the FormPage belongs to
    """

    identifier: str
    page_number: int
    required: Optional[Union[bool, None]]
    duplicates: Optional[Union[bool, None]]
    additional_args: Optional[Union[Dict[str, Any], None]]
    form_meta: Optional[Union[Metadata, None]]

    class Config:
        arbitrary_types_allowed = True

    def __repr__(self):
        return f"""
        Form page:
            page_number: {self.page_number}
            identifier: {self.identifier}
            required: {self.required}
            duplicates: {self.duplicates}
            additional_args: {self.additional_args}
        """

    @validator("identifier", allow_reuse=True)
    def _validate_identifier(cls, v):
        try:
            re.compile(v)
        except re.error:
            raise re.error(
                "Form page identifier is not\n" "a valid regular expression."
            )
        return v

    @validator("form_meta", allow_reuse=True)
    def _validate_form_meta(cls, v):
        form_meta_cond = isinstance(v, FormMetadata) or v is None
        assert (
            form_meta_cond
        ), "form_meta property should be None or a FormMetadata object."
        return v

    @classmethod
    def from_dict(
        cls, fp_dict: dict, form_meta: Optional[Union[Metadata, None]] = None
    ):
        """Creates a FormPage from a dictionary

        Takes a dictionary representing a FormPage
        and unpacks it into a FormPage object.

        Params:
            fp_dict (Dict[str, Any]): A dictionary
                representing a FormPage

        Returns:
            (FormPage): FormPage object
        """
        fp_dict_copy = deepcopy(fp_dict)

        for k, v in fp_dict.items():
            if k not in {
                "page_number",
                "identifier",
                "required",
                "duplicates",
                "additional_args",
            }:
                if "additional_args" not in fp_dict:
                    fp_dict_copy["additional_args"] = {}

                fp_dict_copy["additional_args"][k] = v

        if form_meta is not None:
            fp_dict_copy["form_meta"] = form_meta

        fp = cls(**fp_dict_copy)

        return fp

    def to_dict(self) -> Dict:
        """Outputs FormPage to a dictionary

        Takes a FormPage and returns a dictionary
        representing the FormPage.

        Returns:
            (Dict): FormPage object
        """
        additional_args = {} if self.additional_args is None else self.additional_args

        return {
            "page_number": self.page_number,
            "identifier": self.identifier,
            "required": self.required,
            "duplicates": self.duplicates,
            **additional_args,
        }

    def form_fields(self, form_meta: Optional[Metadata] = None) -> List[FormField]:
        """Returns the page's list of FormFields

        Retirns a list of FormFields for the form
        page based on the parent FormMetadata given.

        Params:
            form_meta (Optional[FormMetadata]):
                Parent FormMetadata object

        Returns:
            (List[FormField]): List of FormFields
        """
        if form_meta is not None:
            self.form_meta = form_meta

        if self.form_meta is None:
            raise ValueError(
                "FormMetadata must be passed to the FormPage for this method."
            )

        ffs = self.form_meta.form_fields
        fpfs = [ff for ff in ffs if ff.page_number == self.page_number]

        return fpfs

    def form_field_names(self, form_meta=None) -> List[str]:
        """Returns the page's list of form fieldnames

        Retirns a list of form fieldnames for the form
        page based on the parent FormMetadata given.

        Params:
            form_meta (Optional[FormMetadata]):
                Parent FormMetadata object

        Returns:
            (List[str]): List of form fieldnames
        """
        fpfs = self.form_fields(form_meta=form_meta)
        fpfns = [ff.name for ff in fpfs]
        return fpfns


class FormMetadata(Metadata):
    """Form metadata class.

    This is an extension of the mopjap-metadata Metadata class
    to represent a form. Additional attributes to those
    found in the base Metadata class are listed below.

    Attributes:
        form_identifier (str): Regular expression that identifies a
            form
        from_template (str): Directory where the form template images
            can be found
        form_formats (List[str]): List of valid formats for the form
            (e.g. pdf, tif)
        form_fields (List[FormField]): List of fields listed in the
            form metadata
        form_pages (List[Union[FormPage, Dict[str, Any]]]): List of
            form pages included in the form
        form_page_numbers (List[int]): List of form page numbers
            included in the form
        excluded_sections (List[str]): List of regular expressions
            representing pages that should not be considered part of
            the form
    """

    form_template = MetadataProperty()
    form_formats = MetadataProperty()
    form_identifier = MetadataProperty()
    excluded_sections = MetadataProperty()

    def __init__(
        self,
        name: Optional[str] = "",
        description: Optional[str] = "",
        sensitive: Optional[bool] = False,
        columns: Optional[Union[List[Dict], None]] = None,
        primary_key: Optional[Union[List[str], None]] = None,
        partitions: Optional[Union[List[str], None]] = None,
        force_partition_order: Optional[Union[str, None]] = None,
        form_pages: Optional[Union[List[Dict], None]] = None,
        form_formats: Optional[Union[List[str], None]] = None,
        form_identifier: Optional[str] = "",
        excluded_sections: Optional[Union[List[str], None]] = None,
        form_template: Optional[str] = "",
    ) -> None:
        super().__init__(
            name=name,
            description=description,
            sensitive=sensitive,
            columns=columns,
            primary_key=primary_key,
            partitions=partitions,
            force_partition_order=force_partition_order,
        )

        if form_pages is not None:
            self._data["form_pages"] = [FormPage.from_dict(p) for p in form_pages]
        else:
            self._data["form_pages"] = []

        self._data["form_formats"] = form_formats
        self._data["form_identifier"] = form_identifier
        self._data["from_template"] = form_template
        self._data["excluded_sections"] = (
            excluded_sections if excluded_sections is not None else []
        )

        self.validate()

    @property
    def form_pages(self):
        pages = self._data["form_pages"]
        fp = [FormPage.from_dict(p, form_meta=self) for p in pages]
        return fp

    @form_pages.setter
    def form_pages(self, form_pages: list):
        fp = [p.to_dict() if isinstance(p, FormPage) else p for p in form_pages]
        self._data["form_pages"] = fp
        self.validate()

    @property
    def form_fields(self):
        columns = deepcopy(self.columns)
        fields = [FormField.from_dict(c) for c in columns]
        return fields

    @property
    def form_page_numbers(self) -> List[int]:
        fps = self.form_pages
        fpns = [fp.page_number for fp in fps]
        return fpns

    def validate(self):
        super().validate()

        if "file_format" in self.__dict__:
            if self.file_format != "":
                warn(
                    """
                    FormMetadata should not have a
                    file_format specified. Please use
                    form_formats instead.
                    """
                )

        self._validate_form_attribute(attribute="form_formats", type=list)
        self._validate_form_attribute(attribute="excluded_sections", type=list)
        self._validate_form_attribute(attribute="form_identifier", type=str)
        self._validate_form_attribute(attribute="form_template", type=str)
        self._validate_columns()
        self._validate_form_pages()

    def _validate_form_attribute(self, attribute: str, type: object) -> None:
        attribute_obj = getattr(self, attribute)
        if attribute_obj is not None:
            if not isinstance(attribute_obj, type):
                raise TypeError(f"'{attribute}' must be of type '{type}'")

    def _validate_columns(self) -> None:
        columns = deepcopy(self.columns)
        for col in columns:
            if "bounding_box" not in col:
                raise ValueError(
                    """
                    Bounding boxes must be specfied for FormMetadata columns
                    """
                )

            else:
                _ = BoundingBox.validate_bbdict(col["bounding_box"])

    def _validate_form_pages(self) -> None:
        pages = [FormPage.from_dict(p) for p in self._data.get("form_pages", [])]

        if pages:
            fp_numbers = [p.page_number for p in pages]

            ffp_numbers = [self.form_field(c).page_number for c in self.column_names]

            fp_numbers = set(fp_numbers)
            ffp_numbers = set(ffp_numbers)

            if not ffp_numbers.issubset(fp_numbers):
                raise ValidationError(
                    "Form fields require a page not listed\n"
                    "in form_pages:\n"
                    f"form pages: {str(fp_numbers)}\n"
                    f"form field pages: {str(ffp_numbers)}"
                )

            max_fp = max(fp_numbers)
            full_fp = set(range(1, max_fp + 1))
            if full_fp != fp_numbers:
                raise ValidationError("There are missing pages in form_pages")

    def form_field(self, field_name: str) -> FormField:
        """Returns the specified form field

        Returns the form field contained in the form
        metadata with the given name.

        Params:
            field_name (str): The name of the form
                field to return

        Returns:
            (FormField): FormField object
        """
        column = deepcopy(self.get_column(field_name))
        return FormField.from_dict(column)

    def form_page(self, page_number: int) -> FormPage:
        """Returns the specified form page

        Returns the form page contained in the form
        metadata with the given page number.

        Params:
            page_number (int): The page number
                of the form page to return

        Returns:
            (FormPage): FormPage object
        """
        fps = [fp for fp in self.form_pages if fp.page_number == page_number]
        if len(fps) == 0:
            raise ValueError("Page doesn't exist in Form Metadata.")
        elif len(fps) > 1:
            raise ValueError("Duplicate pages exist in Form Metadata.")
        return fps[0]
