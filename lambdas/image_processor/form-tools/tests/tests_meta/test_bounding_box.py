import pytest
from jsonschema.exceptions import ValidationError


class TestBoundingBox:
    def setup_test(self):
        from form_tools.form_meta.bounding_box import BoundingBox

        return BoundingBox

    @pytest.mark.parametrize(
        "bb_val, remainder, bb_format, expected",
        [
            (
                {"left": 2, "top": 4, "width": 1, "height": 3},
                {
                    "right": 3,
                    "bottom": 7,
                },
                {},
                True,
            ),
            (
                {
                    "right": 3,
                    "bottom": 7,
                    "width": 1,
                    "height": 3,
                },
                {
                    "left": 2,
                    "top": 4,
                },
                {},
                True,
            ),
            (
                {
                    "right": 3,
                    "bottom": 7,
                    "left": 2,
                    "top": 4,
                },
                {
                    "width": 1,
                    "height": 3,
                },
                {},
                True,
            ),
            (
                {
                    "right": 3,
                    "bottom": 7,
                    "left": 2,
                    "width": 4,
                },
                None,
                {},
                False,
            ),
            (
                {
                    "right": 3,
                    "bottom": 7,
                    "left": 2,
                },
                None,
                {},
                False,
            ),
            (
                (2, 4, 1, 3),
                {
                    "right": 3,
                    "bottom": 7,
                },
                {"bb_format": "ltwh"},
                True,
            ),
            (
                (3, 7, 1, 3),
                {
                    "left": 2,
                    "top": 4,
                },
                {"bb_format": "rbwh"},
                True,
            ),
            (
                [2, 4, 1, 3],
                {
                    "right": 3,
                    "bottom": 7,
                },
                {"bb_format": "ltwh"},
                True,
            ),
            (
                [3, 7, 1, 3],
                {
                    "left": 2,
                    "top": 4,
                },
                {"bb_format": "rbwh"},
                True,
            ),
            (
                [3, 7, 1, 3],
                {
                    "width": 2,
                    "top": 4,
                },
                {"bb_format": "rblh"},
                False,
            ),
            (
                {
                    "left": 100,
                    "width": 100,
                    "top": 600,
                    "height": 20,
                },
                {"right": 200, "bottom": 620},
                {},
                True,
            ),
        ],
    )
    def test_bb_from(self, bb_val, remainder, bb_format, expected):
        bbclass = self.setup_test()
        if expected:
            bb = bbclass.from_infer(bb_val, **bb_format)

            if bb_format:
                bb_dict = {
                    bbclass.lookup[v]: bb_val[i]
                    for i, v in enumerate(bb_format["bb_format"])
                }
            else:
                bb_dict = bb_val

            comparison = {**bb_dict, **remainder}

            for dim, val in comparison.items():
                dim_value = getattr(bb, dim)
                assert dim_value == val
        else:
            with pytest.raises(
                (ValidationError, ValueError),
            ):
                bb = bbclass.from_infer(bb_val, **bb_format)

    @pytest.mark.parametrize(
        "format, expected",
        [
            (
                "ltwh",
                {"left": 2, "top": 4, "width": 1, "height": 3},
            ),
            (
                "rbwh",
                {
                    "right": 3,
                    "bottom": 7,
                    "width": 1,
                    "height": 3,
                },
            ),
            (
                "rblt",
                {
                    "right": 3,
                    "bottom": 7,
                    "left": 2,
                    "top": 4,
                },
            ),
        ],
    )
    def test_bb_to_dict(self, format, expected):
        bbclass = self.setup_test()
        bb = bbclass(2, 4, 1, 3)
        bb_dict = bb.to_dict(bb_format=format)
        assert bb_dict == expected

    @pytest.mark.parametrize(
        "format, expected",
        [
            (
                "ltwh",
                (2, 4, 1, 3),
            ),
            (
                "rbwh",
                (3, 7, 1, 3),
            ),
            (
                "rblt",
                (3, 7, 2, 4),
            ),
        ],
    )
    def test_bb_to_tuple(self, format, expected):
        bbclass = self.setup_test()
        bb = bbclass(2, 4, 1, 3)
        bb_tuple = bb.to_tuple(bb_format=format)
        assert bb_tuple == expected

    @pytest.mark.parametrize(
        "format, expected",
        [
            (
                "ltwh",
                [2, 4, 1, 3],
            ),
            (
                "rbwh",
                [3, 7, 1, 3],
            ),
            (
                "rblt",
                [3, 7, 2, 4],
            ),
        ],
    )
    def test_bb_to_list(self, format, expected):
        bbclass = self.setup_test()
        bb = bbclass(2, 4, 1, 3)
        bb_list = bb.to_list(bb_format=format)
        assert bb_list == expected
