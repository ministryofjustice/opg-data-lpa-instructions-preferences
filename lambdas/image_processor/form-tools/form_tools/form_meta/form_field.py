from copy import deepcopy
from pydantic import BaseModel
from typing import Optional, Union, Dict, Any

from .bounding_box import BoundingBox


class FormField(BaseModel):
    """Form field class.

    Represents a field in a form template, typically a PDF
    form.

    Attributes:
        name (Optional[str]): Field name
        type (Optional[str]): Data type of field entry
        nullable (Optional[Union[bool, None]]): Whether null values are valid
        page_number (Optional[Union[int, None]]): Page number in form for the field
        bounding_box (Optional[Union[BoundingBox, None]]): BoundingBox object
            for the location of the field on the given form template page
        confidence (Optional[Union[float, None]]): Confidence level, between 0 and 1.
        additional_args (Optional[Union[Dict[str, Any], None]]): Additional arguments
            to store for the field.
    """

    name: Optional[str] = ""
    type: Optional[str] = ""
    page_number: Optional[Union[int, None]]
    nullable: Optional[Union[bool, None]]
    bounding_box: Optional[Union[BoundingBox, None]]
    confidence: Optional[Union[float, None]]
    additional_args: Optional[Union[Dict[str, Any], None]]

    class Config:
        arbitrary_types_allowed = True

    def __repr__(self):
        return f"""
        Form field:
            name: {self.name}
            type: {self.type}
            page_number: {self.page_number}
            nullable: {self.nullable}
            bounding_box: {self.bounding_box.__repr__(hide=True)}
            confidence: {self.confidence}
            additional_args: {self.additional_args}
        """

    @classmethod
    def from_dict(cls, ff_dict: dict):
        """Creates a FormField from a dictionary

        Takes a dictionary representing a FormField
        and unpacks it into a FormField object.

        Params:
            ff_dict (Dict[str, Any]): A dictionary
                representing a FormField

        Returns:
            (FormField): FormField object
        """
        if "bounding_box" in ff_dict:
            bb = BoundingBox.from_dict(ff_dict["bounding_box"])
            ff_dict["bounding_box"] = bb

        ff_dict_copy = deepcopy(ff_dict)
        for k, v in ff_dict_copy.items():
            if k not in {
                "name",
                "type",
                "page_number",
                "nullable",
                "bounding_box",
                "confidence",
                "additional_args",
            }:
                if "additional_args" not in ff_dict:
                    ff_dict["additional_args"] = {}

                ff_dict["additional_args"][k] = v

        return cls(**ff_dict)

    def to_dict(self, bb_format: Optional[str] = "ltwh"):
        ff_dict = self.dict()
        ff_dict["bounding_box"] = ff_dict["bounding_box"].to_dict(bb_format)
        updated_ff_dict = {k: v for k, v in ff_dict.items() if v is not None}
        return updated_ff_dict
