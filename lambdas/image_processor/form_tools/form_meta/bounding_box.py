from jsonschema import validate
from jsonschema.exceptions import ValidationError
from typing import Any, Tuple, List, Dict, Optional


class BoundingBox:
    """Bounding box class.

    Represents a bounding box region of an image. (0, 0) is
    assumed to be the top-left hand side of the image.

    Attributes:
        left (int): Left coordinate value for bounding box
        top (int): Top coordinate value for bounting box
        width (int): Width of the bounding box
        height (int): Height of the bounding box
    """

    lookup = {
        "l": "left",
        "b": "bottom",
        "r": "right",
        "t": "top",
        "h": "height",
        "w": "width",
    }

    schemas = {
        "ltwh": {
            "type": "object",
            "properties": {
                "left": {"type": "integer"},
                "top": {"type": "integer"},
                "width": {"type": "integer"},
                "height": {"type": "integer"},
            },
            "required": ["left", "top", "width", "height"],
        },
        "ltrb": {
            "type": "object",
            "properties": {
                "left": {"type": "integer"},
                "top": {"type": "integer"},
                "right": {"type": "integer"},
                "bottom": {"type": "integer"},
            },
            "required": ["left", "top", "right", "bottom"],
        },
        "rbwh": {
            "type": "object",
            "properties": {
                "right": {"type": "integer"},
                "bottom": {"type": "integer"},
                "width": {"type": "integer"},
                "height": {"type": "integer"},
            },
            "required": ["right", "bottom", "width", "height"],
        },
    }

    def __init__(self, left: int, top: int, width: int, height: int):
        self.bottom = top + height
        self.left = left
        self.width = width
        self.height = height
        self.right = left + width
        self.top = top

    def __repr__(self, hide: Optional[bool] = False):
        tl_coord = f"({self.left}, {self.top})"
        tr_coord = f"({self.right}, {self.top})"
        bl_coord = f"({self.left}, {self.bottom})"
        br_coord = f"({self.right}, {self.bottom})"

        tlen = len(tl_coord) + len(tr_coord)
        blen = len(bl_coord) + len(br_coord)

        diff = tlen - blen
        bdash = "".join(["-"] * diff) if diff > 0 else ""
        tdash = "".join(["-"] * -diff) if diff < 0 else ""

        tline = f"{tl_coord} --------{tdash} {tr_coord}"
        bline = f"{bl_coord} --------{bdash} {br_coord}"
        max_line = max(len(tline), len(bline))
        sep = "".join([" "] * (max_line - 2))
        height_line = "|" + sep + "|"

        bb_repr = f"""
        Bounding box:
            {tline}
            {height_line}
            {height_line}
            {height_line}
            {height_line}
            {height_line}
            {bline}
        """

        bb_repr_noh = f"""
            {tline}
            {height_line}
            {height_line}
            {height_line}
            {height_line}
            {height_line}
            {bline}
        """

        bb_repr = bb_repr_noh if hide else bb_repr

        return bb_repr

    @classmethod
    def validate_bbdict(cls, bb_dict: Dict[str, int]) -> str:
        """Classmethod for validating a bounding box dictionary.

        Method takes a bounding box dictionary and compares it with
        available schemas, and then returns the matching format
        (e.g. ltwh, ltrb etc.).

        Params:
            bb_dict (Dict[str, int]): Bounding box dictionary

        Returns:
            (str): The corresponding schema type for the bounding box

        """
        i = 0
        schemas = cls.schemas
        for schema_key, schema in schemas.items():
            try:
                validate(instance=bb_dict, schema=schema)
                valid_schema_key = schema_key
            except ValidationError:
                i += 1

        if i == 3:
            raise ValidationError(
                "Bounding box dictionary doesn't match expected schema"
            )

        else:
            return valid_schema_key

    @staticmethod
    def validate_bb_format(bb_format: str):
        """Validates bounding box schema format.

        Takes a bounding box schema format string and checks
        wheteher all necessary dimensions have been provided.
        Raises a value error if not valid.

        Params:
            bb_format (str): Bounding box schema format (e.g. ltwh, ltrb etc.)
        """
        bb_format = set(bb_format)
        if len(bb_format) != 4:
            raise ValueError(
                "bb_format should be a string of length 4. "
                "Characters must be one of l, b, h, w, r, t."
            )

        ltwh_ft = set("ltwh")
        ltrb_ft = set("ltrb")
        rbwh_ft = set("rbwh")

        if bb_format != ltwh_ft and bb_format != ltrb_ft and bb_format != rbwh_ft:
            raise ValueError(
                "bb_format should be, up to rearrangement,\n"
                "one of:\n"
                "1. ltwh\n"
                "2. ltrb\n"
                "3. rbwh"
            )

    @classmethod
    def from_dict(cls, bb_dict: Dict[str, int]):
        """Creates a BoundingBox from a dictionary.

        Takes a bounding box dictionary and returns a BoundingBox
        object if the dictionary meets the expected format.
        Otherwise raises an error.

        Params:
            bb_dict (Dict[str, int]): Bounding box dictionary

        Returns:
            (BoundingBox): BoundingBox object
        """
        bb_key = cls.validate_bbdict(bb_dict)

        if set(bb_key) == set("ltrb"):
            bb_dict["width"] = bb_dict["right"] - bb_dict["left"]
            bb_dict["height"] = bb_dict["bottom"] - bb_dict["top"]

        elif set(bb_key) == set("whrb"):
            bb_dict["left"] = bb_dict["right"] - bb_dict["width"]
            bb_dict["top"] = bb_dict["bottom"] - bb_dict["height"]

        bb = cls(
            left=bb_dict["left"],
            top=bb_dict["top"],
            width=bb_dict["width"],
            height=bb_dict["height"],
        )

        return bb

    @classmethod
    def from_tuple(
        cls, bb_tuple: Tuple[int, int, int, int], bb_format: Optional[str] = "ltwh"
    ):
        """Creates a BoundingBox from a tuple.

        Takes a tuple and bounding box format and returns a BoundingBox
        object if a valid format is passed. Otherwise raises an error.
        Defaults to using the ltwh format.

        Params:
            bb_tuple (Tuple[int, int, int, int]): Bounding box tuple
            bb_format (Optional[str]): A valid bounding box schema format (e.g.
                ltwh, rbwh etc.)

        Returns:
            (BoundingBox): BoundingBox object
        """
        BoundingBox.validate_bb_format(bb_format=bb_format)
        if len(bb_tuple) != 4:
            raise TypeError("bb_typle must be a 4-tuple.")
        lookup = BoundingBox.lookup
        bb_dict = {}
        for i, coord in enumerate(bb_format):
            full_coord = lookup[coord]
            bb_dict[full_coord] = bb_tuple[i]

        return BoundingBox.from_dict(bb_dict=bb_dict)

    @classmethod
    def from_list(
        cls,
        bb_list: List[int],
        bb_format: Optional[str] = "ltwh",
    ):
        """Creates a BoundingBox from a list.

        Takes a list and bounding box format and returns a BoundingBox
        object if a valid format is passed. Otherwise raises an error.
        Defaults to using the ltwh format.

        Params:
            bb_list (List[int]): Bounding box list
            bb_format (Optional[str]): A valid bounding box schema format (e.g.
                ltwh, rbwh etc.)

        Returns:
            (BoundingBox): BoundingBox object
        """
        bb_tuple = tuple(bb_list)
        return BoundingBox.from_tuple(bb_tuple, bb_format=bb_format)

    @classmethod
    def from_infer(cls, bb_object: Any, **bb_conversion_kwargs):
        """Creates a BoundingBox from an object, if possible

        Takes a list and bounding box format and returns a BoundingBox
        object if a valid format is passed. Otherwise raises an error.
        Defaults to using the ltwh format.

        Params:
            bb_object (Any): A valid boudning box dictionary, tuple or list
            **bb_conversion_kwargs: Keyword arguments passed to `from_list`
                and `from_tuple`.

        Returns:
            (BoundingBox): BoundingBox object
        """
        bb_type = type(bb_object).__name__
        try:
            from_mthd = getattr(BoundingBox, f"from_{bb_type}")

        except AttributeError:
            raise TypeError("BoundingBox cannot convert\n" f"object of type {bb_type}")

        bb = from_mthd(bb_object, **bb_conversion_kwargs)

        return bb

    def to_dict(self, bb_format: Optional[str] = "ltwh") -> Dict[str, int]:
        """Converts the BoundingBox to a dictionary

        Takes the BoundingBox and returns a dictionary
        based on the bounding box schema format supplied.

        Params:
            bb_format (Optional[str]): A valid bounding box schema format (e.g.
                ltwh, rbwh etc.)

        Returns:
            (Dict[str, int]): Dictionary representing the bounding box
        """
        self.validate_bb_format(bb_format=bb_format)
        bb_dict = {}
        bb_format = set(bb_format)

        if "l" in bb_format:
            bb_dict["left"] = self.left
        if "r" in bb_format:
            bb_dict["right"] = self.right
        if "w" in bb_format:
            bb_dict["width"] = self.width
        if "t" in bb_format:
            bb_dict["top"] = self.top
        if "h" in bb_format:
            bb_dict["height"] = self.height
        if "b" in bb_format:
            bb_dict["bottom"] = self.bottom
        if not bb_format.issubset(["l", "b", "t", "r", "w", "h"]):
            raise ValueError("bb_format characters must be one of l, " "b, h, w, r, t.")

        return bb_dict

    def to_tuple(self, bb_format: str = "ltrb") -> Tuple[int, int, int, int]:
        """Converts the BoundingBox to a tuple

        Takes the BoundingBox and returns a tuple
        based on the bounding box schema format supplied.

        Params:
            bb_format (Optional[str]): A valid bounding box schema format (e.g.
                ltwh, rbwh etc.)

        Returns:
            (Tuple[int, int, int, int]): Tuple representing the bounding box
        """
        bb_dict = self.to_dict(bb_format=bb_format)
        bb_tuple = tuple()
        lookup = BoundingBox.lookup
        for coord in bb_format:
            full_bb_coord = lookup[coord]
            bb_tuple += (bb_dict[full_bb_coord],)

        return bb_tuple

    def to_list(self, bb_format: str = "ltrb") -> List[int]:
        """Converts the BoundingBox to a list

        Takes the BoundingBox and returns a list
        based on the bounding box schema format supplied.

        Params:
            bb_format (Optional[str]): A valid bounding box schema format (e.g.
                ltwh, rbwh etc.)

        Returns:
            (List[int]): Tuple representing the bounding box
        """
        bb_tuple = self.to_tuple(bb_format=bb_format)
        bb_list = list(bb_tuple)
        return bb_list
