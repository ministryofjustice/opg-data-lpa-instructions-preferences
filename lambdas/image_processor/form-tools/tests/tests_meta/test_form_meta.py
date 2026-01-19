import pytest


class TestFormMetadata:
    test_meta_location = "tests/tests_meta/data/form_metadata/test.json"
    expected_page_numbers = [1, 2]

    def setup_test(self):
        from .form_tools.form_meta.form_meta import FormMetadata

        return FormMetadata.from_json(self.test_meta_location)

    @staticmethod
    def convert_field_to_dict(field):
        field_dict = field.dict()
        field_dict["bounding_box"] = field_dict["bounding_box"].to_dict()
        return field_dict

    @pytest.mark.parametrize(
        "field_name, expected",
        [
            (
                "my_string_field",
                {
                    "name": "my_string_field",
                    "type": "string",
                    "page_number": 1,
                    "nullable": None,
                    "bounding_box": {
                        "left": 100,
                        "width": 100,
                        "top": 600,
                        "height": 20,
                    },
                    "confidence": None,
                    "additional_args": None,
                },
            ),
            (
                "my_other_string_field",
                {
                    "name": "my_other_string_field",
                    "type": "string",
                    "page_number": 1,
                    "nullable": None,
                    "bounding_box": {
                        "left": 250,
                        "width": 1000,
                        "top": 400,
                        "height": 30,
                    },
                    "confidence": None,
                    "additional_args": None,
                },
            ),
            (
                "my_int_field",
                {
                    "name": "my_int_field",
                    "type": "int64",
                    "page_number": 2,
                    "nullable": True,
                    "bounding_box": {
                        "left": 113,
                        "width": 107,
                        "top": 741,
                        "height": 52,
                    },
                    "confidence": 0.8,
                    "additional_args": {"some_extra_info": 32},
                },
            ),
            (
                "my_bool_field",
                {
                    "name": "my_bool_field",
                    "type": "bool",
                    "page_number": 2,
                    "nullable": None,
                    "bounding_box": {
                        "left": 247,
                        "width": 907,
                        "top": 741,
                        "height": 52,
                    },
                    "confidence": None,
                    "additional_args": None,
                },
            ),
        ],
    )
    def test_form_field(self, field_name, expected):
        form_meta = self.setup_test()
        form_field = form_meta.form_field(field_name)
        form_field_dict = form_field.dict()
        form_field_dict["bounding_box"] = form_field_dict["bounding_box"].to_dict()
        assert form_field_dict == expected

    @pytest.mark.parametrize(
        "page_number, expected",
        [
            (
                1,
                {
                    "identifier": "first page",
                    "page_number": 1,
                    "required": True,
                    "duplicates": False,
                },
            ),
            (
                2,
                {
                    "page_number": 2,
                    "identifier": "second page",
                    "required": True,
                    "duplicates": False,
                    "my_extra_property": True,
                },
            ),
        ],
    )
    def test_form_page(self, page_number, expected):
        form_meta = self.setup_test()
        form_page = form_meta.form_page(page_number)
        form_page_dict = form_page.to_dict()
        assert form_page_dict == expected

    def test_form_page_numbers(self):
        form_meta = self.setup_test()
        form_page_numbers = form_meta.form_page_numbers
        assert form_page_numbers == self.expected_page_numbers

    @pytest.mark.parametrize(
        "page_number, field_names",
        [
            (1, ["my_string_field", "my_other_string_field"]),
            (2, ["my_int_field", "my_bool_field"]),
        ],
    )
    def test_form_field_names(self, page_number, field_names):
        form_meta = self.setup_test()
        form_page = form_meta.form_page(page_number)
        form_page_fieldnames = form_page.form_field_names(form_meta=form_meta)
        assert form_page_fieldnames == field_names

    @pytest.mark.parametrize(
        "page_number, fields",
        [
            (
                1,
                [
                    {
                        "name": "my_string_field",
                        "type": "string",
                        "page_number": 1,
                        "nullable": None,
                        "bounding_box": {
                            "left": 100,
                            "width": 100,
                            "top": 600,
                            "height": 20,
                        },
                        "confidence": None,
                        "additional_args": None,
                    },
                    {
                        "name": "my_other_string_field",
                        "type": "string",
                        "page_number": 1,
                        "nullable": None,
                        "bounding_box": {
                            "left": 250,
                            "width": 1000,
                            "top": 400,
                            "height": 30,
                        },
                        "confidence": None,
                        "additional_args": None,
                    },
                ],
            ),
            (
                2,
                [
                    {
                        "name": "my_int_field",
                        "type": "int64",
                        "page_number": 2,
                        "nullable": True,
                        "bounding_box": {
                            "left": 113,
                            "width": 107,
                            "top": 741,
                            "height": 52,
                        },
                        "confidence": 0.8,
                        "additional_args": {"some_extra_info": 32},
                    },
                    {
                        "name": "my_bool_field",
                        "type": "bool",
                        "page_number": 2,
                        "nullable": None,
                        "bounding_box": {
                            "left": 247,
                            "width": 907,
                            "top": 741,
                            "height": 52,
                        },
                        "confidence": None,
                        "additional_args": None,
                    },
                ],
            ),
        ],
    )
    def test_form_fields(self, page_number, fields):
        form_meta = self.setup_test()
        form_page = form_meta.form_page(page_number)
        form_page_fields = form_page.form_fields(form_meta=form_meta)
        form_fields = [self.convert_field_to_dict(ff) for ff in form_page_fields]
        assert form_fields == fields
