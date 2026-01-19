import pytest


@pytest.mark.parametrize(
    "input, output",
    [
        (
            {
                "name": "my_field",
                "type": "int32",
                "page_number": 2,
                "nullable": False,
                "bounding_box": {"left": 1, "top": 0, "height": 2, "width": 3},
                "confidence": 0.95,
                "additional_args": {"my_special_parameter": "hello"},
            },
            {
                "name": "my_field",
                "type": "int32",
                "page_number": 2,
                "nullable": False,
                "bounding_box": {
                    "left": 1,
                    "top": 0,
                    "height": 2,
                    "width": 3,
                },
                "confidence": 0.95,
                "additional_args": {"my_special_parameter": "hello"},
            },
        ),
        (
            {
                "name": "my_field",
                "type": "int32",
                "page_number": "2",
                "nullable": "False",
                "bounding_box": {"left": 1, "top": 0, "height": 2, "width": 3},
                "confidence": "0.95",
            },
            {
                "name": "my_field",
                "type": "int32",
                "page_number": 2,
                "nullable": False,
                "bounding_box": {
                    "left": 1,
                    "top": 0,
                    "height": 2,
                    "width": 3,
                },
                "confidence": 0.95,
                "additional_args": None,
            },
        ),
    ],
)
def test_form_field(input, output):
    from .form_tools.form_meta.form_field import FormField

    form_field = FormField.from_dict(input)
    form_field_dict = form_field.dict()
    form_field_dict["bounding_box"] = form_field_dict["bounding_box"].to_dict()
    assert form_field_dict == output
