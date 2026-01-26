import re
import pytest
import numpy as np


class TestFormOperator:
    DEFAULT_CONFIG_PATH = "tests/tests_operators/data/configs/valid_config.yml"

    @pytest.mark.parametrize(
        "config, expected",
        [
            ("tests/tests_operators/data/configs/invalid_config.yml", False),
            ("tests/tests_operators/data/configs/valid_config.yml", True),
            ("tests/tests_operators/data/configs/valid_config2.yml", True),
            ("tests/tests_operators/data/configs/valid_config3.yml", True),
        ],
    )
    def test_attributes(self, config, expected):
        from form_tools.form_operators.form_operator import FormOperator
        from form_tools.form_operators.form_page_operator import FormPageOperator

        if expected:
            operator = FormOperator.create_from_config(config)
            page_operator = FormPageOperator.create_from_config(config)

            assert operator.form_page_operator.dict() == page_operator.dict()
            assert operator.config.dict() == page_operator.config.dict()

        else:
            with pytest.raises(Exception):
                FormOperator.create_from_config(config)

    @pytest.mark.parametrize(
        "form_meta_directory, expected",
        [
            ("tests/tests_operators/data/configs", []),
            ("tests/tests_operators/data/form_metadata", ["testid", "test"]),
        ],
    )
    def test_form_meta_store(self, form_meta_directory, expected):
        from form_tools.form_operators.form_operator import FormOperator

        meta_store = FormOperator.form_meta_store(form_meta_directory)
        assert sorted(expected) == sorted([k for k in meta_store])
