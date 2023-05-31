from unittest.mock import patch, MagicMock
import pytest
from app.utility.path_selection_service import PathSelectionService


@pytest.fixture
def path_selection_service():
    return PathSelectionService("9999")


def test_get_continuation_sheet_type(path_selection_service):
    assert path_selection_service.get_continuation_sheet_type(True, True) == "BOTH"
    assert (
        path_selection_service.get_continuation_sheet_type(True, False)
        == "INSTRUCTIONS"
    )
    assert (
        path_selection_service.get_continuation_sheet_type(False, True) == "PREFERENCES"
    )
    assert path_selection_service.get_continuation_sheet_type(False, False) == "NEITHER"


def test_get_selected_paths_for_upload(path_selection_service):
    # Mock input parameters
    paths = [
        "/path/to/instructions/meta=lp1h/field_name=instructions/",
        "/path/to/preferences/meta=lp1h/field_name=preferences/",
        "/path/to/instructions/meta=lph/field_name=continuation_checkbox_instructions",
        "/path/to/preferences/meta=lph/field_name=continuation_checkbox_preferences",
        "/path/to/continuation_1/meta=lpc/field_name=preferences_checkbox_p1",
        "/path/to/continuation_1/meta=lpc/field_name=instructions_checkbox_p2",
        "/path/to/continuation_1/meta=lpc/field_name=continuation_sheet_p1",
        "/path/to/continuation_1/meta=lpc/field_name=continuation_sheet_p2",
    ]
    continuation_keys_to_use = ["continuation_1"]

    # Mock objects
    mock_response = {
        "path_selection": {
            "instructions": "/path/to/instructions/meta=lp1h/field_name=instructions/",
            "preferences": "/path/to/preferences/meta=lp1h/field_name=preferences/",
        },
        "continuation_instructions": True,
        "continuation_preferences": False,
    }
    mock_continuation_sheets = {
        "p1": {
            "path": "/path/to/continuation_1/meta=lpc/field_name=continuation_sheet_p1",
            "type": "preferences",
        },
        "p2": {
            "path": "/path/to/continuation_1/meta=lpc/field_name=continuation_sheet_p2",
            "type": "instructions",
        },
    }

    # Patch the mock methods
    with patch.object(
        path_selection_service,
        "find_instruction_and_preference_paths",
        return_value=mock_response,
    ):
        with patch.object(
            path_selection_service, "get_continuation_sheet_type", return_value="BOTH"
        ):
            with patch.object(
                path_selection_service,
                "get_continuation_sheet_paths",
                return_value=mock_continuation_sheets,
            ):
                # Call the method under test
                result = path_selection_service.get_selected_paths_for_upload(
                    paths, continuation_keys_to_use
                )

    # Verify the expected output
    expected_result = {
        "instructions": "/path/to/instructions/meta=lp1h/field_name=instructions/",
        "preferences": "/path/to/preferences/meta=lp1h/field_name=preferences/",
        "continuation_instructions_1": "/path/to/continuation_1/meta=lpc/field_name=continuation_sheet_p2",
        "continuation_preferences_1": "/path/to/continuation_1/meta=lpc/field_name=continuation_sheet_p1",
    }
    assert result == expected_result


def test_find_instruction_and_preference_paths(path_selection_service, monkeypatch):
    # Test case where both instructions and preferences files are found
    path_selection = {"instructions": "", "preferences": ""}
    paths = [
        "/path/to/instructions/meta=lp1f/field_name=instructions/",
        "/path/to/preferences/meta=lp1f/field_name=preferences/",
    ]
    result = path_selection_service.find_instruction_and_preference_paths(
        path_selection, paths
    )
    assert (
        result["path_selection"]["instructions"]
        == "/path/to/instructions/meta=lp1f/field_name=instructions/"
    )
    assert (
        result["path_selection"]["preferences"]
        == "/path/to/preferences/meta=lp1f/field_name=preferences/"
    )
    assert result["continuation_instructions"] is False
    assert result["continuation_preferences"] is False

    # Test case for continuation sheets
    paths = [
        "/path/to/instructions/meta=lp1h/field_name=instructions/",
        "/path/to/preferences/meta=lp1h/field_name=preferences/",
        "/path/to/instructions/meta=lp1h/field_name=continuation_checkbox_instructions",
        "/path/to/preferences/meta=lp1h/field_name=continuation_checkbox_preferences",
    ]
    detect_marked_checkbox_mock = MagicMock()
    detect_marked_checkbox_mock.return_value = True

    monkeypatch.setattr(
        path_selection_service, "detect_marked_checkbox", detect_marked_checkbox_mock
    )
    result = path_selection_service.find_instruction_and_preference_paths(
        path_selection, paths
    )
    assert (
        result["path_selection"]["instructions"]
        == "/path/to/instructions/meta=lp1h/field_name=instructions/"
    )
    assert (
        result["path_selection"]["preferences"]
        == "/path/to/preferences/meta=lp1h/field_name=preferences/"
    )
    assert result["continuation_instructions"] is True
    assert result["continuation_preferences"] is True


def test_get_continuation_sheet_paths(path_selection_service, monkeypatch):
    continuation_sheet_type = "BOTH"
    path_filter = "continuation_2"

    def mock_detect_marked_checkbox(path):
        if "preferences_checkbox_p1" in path:
            return True
        elif "instructions_checkbox_p2" in path:
            return True
        else:
            return False

    monkeypatch.setattr(
        path_selection_service, "detect_marked_checkbox", mock_detect_marked_checkbox
    )

    # Test case for two paths that have marked checkboxes. Also check filter applies
    paths = [
        "/path/to/continuation_1/meta=lph1/field_name=preferences_checkbox_p1/a.jpg",
        "/path/to/continuation_1/meta=lpc/field_name=preferences_checkbox_p1/b.jpg",
        "/path/to/continuation_1/meta=lpc/field_name=instructions_checkbox_p2/c.jpg",
        "/path/to/continuation_1/meta=lpc/field_name=continuation_sheet_p1/a.jpg",
        "/path/to/continuation_1/meta=lpc/field_name=continuation_sheet_p2/b.jpg",
        "/path/to/continuation_2/meta=lph1/field_name=preferences_checkbox_p1/a.jpg",
        "/path/to/continuation_2/meta=lpc/field_name=preferences_checkbox_p1/b.jpg",
        "/path/to/continuation_2/meta=lpc/field_name=instructions_checkbox_p2/c.jpg",
        "/path/to/continuation_2/meta=lpc/field_name=continuation_sheet_p1/a.jpg",
        "/path/to/continuation_2/meta=lpc/field_name=continuation_sheet_p2/b.jpg",
    ]
    result = path_selection_service.get_continuation_sheet_paths(
        paths, continuation_sheet_type, path_filter
    )

    expected_result = {
        "p1": {
            "path": "/path/to/continuation_2/meta=lpc/field_name=continuation_sheet_p1/a.jpg",
            "type": "preferences",
        },
        "p2": {
            "path": "/path/to/continuation_2/meta=lpc/field_name=continuation_sheet_p2/b.jpg",
            "type": "instructions",
        },
    }

    assert result == expected_result

    # Test case for no detected checkboxes
    paths = [
        "/path/to/continuation_2/meta=lpc/field_name=continuation_sheet_p1/a.jpg",
        "/path/to/continuation_2/meta=lpc/field_name=continuation_sheet_p2/b.jpg",
    ]
    result = path_selection_service.get_continuation_sheet_paths(
        paths, continuation_sheet_type, path_filter
    )

    expected_result = {
        "p1": {
            "path": "/path/to/continuation_2/meta=lpc/field_name=continuation_sheet_p1/a.jpg",
            "type": "neither",
        },
        "p2": {
            "path": "/path/to/continuation_2/meta=lpc/field_name=continuation_sheet_p2/b.jpg",
            "type": "neither",
        },
    }
    assert result == expected_result


def test_merge_continuation_images_into_path_selection(path_selection_service):
    # Define inputs
    path_selection = {
        "preferences": "somepath/preferences",
        "instructions": "somepath/instructions",
    }
    continuation_sheets = {
        "continuation_1": {
            "p1": {
                "path": "somepath/continuation_1_preferences_p1",
                "type": "preferences",
            },
            "p2": {
                "path": "somepath/continuation_1_instructions_p2",
                "type": "instructions",
            },
        },
        "continuation_2": {
            "p1": {
                "path": "somepath/continuation_2_preferences_p1",
                "type": "preferences",
            },
            "p2": {"path": "somepath/continuation_2_random_p2", "type": "neither"},
        },
    }

    # Define expected output
    expected_output = {
        "preferences": "somepath/preferences",
        "instructions": "somepath/instructions",
        "continuation_instructions_1": "somepath/continuation_1_instructions_p2",
        "continuation_preferences_1": "somepath/continuation_1_preferences_p1",
        "continuation_preferences_2": "somepath/continuation_2_preferences_p1",
    }

    # Ensure the function returns the expected output
    output = path_selection_service.merge_continuation_images_into_path_selection(
        path_selection, continuation_sheets
    )
    assert output == expected_output


def test_merge_continuation_images_into_path_selection_edge_combo(
    path_selection_service,
):
    # Define inputs
    path_selection = {
        "preferences": "somepath/preferences",
        "instructions": "somepath/instructions",
    }
    continuation_sheets = {
        "continuation_1": {
            "p1": {
                "path": "somepath/continuation_1/preferences_p1",
                "type": "preferences",
            },
            "p2": {
                "path": "somepath/continuation_1/preferences_p2",
                "type": "preferences",
            },
        },
        "continuation_2": {
            "p1": {"path": "somepath/continuation_2/random_p1", "type": "neither"},
            "p2": {"path": "somepath/continuation_2/random_p2", "type": "neither"},
        },
    }
    # Define expected output
    expected_output = {
        "preferences": "somepath/preferences",
        "instructions": "somepath/instructions",
        "continuation_preferences_1": "somepath/continuation_1/preferences_p1",
        "continuation_preferences_2": "somepath/continuation_1/preferences_p2",
    }

    # Ensure the function returns the expected output
    output = path_selection_service.merge_continuation_images_into_path_selection(
        path_selection, continuation_sheets
    )
    assert output == expected_output


def test_all_mandatory_fragments_and_one_of_fragments_exist(path_selection_service):
    # Case for mandatory fragments exist and one of
    target_string = "This is a test string"
    mandatory_fragments = ["test", "string"]
    one_of_fragments = ["is", "a"]
    result = path_selection_service.string_fragments_in_string(
        target_string, mandatory_fragments, one_of_fragments
    )
    assert result is True

    # Case for not all mandatory fragments exist
    target_string = "This is a test"
    mandatory_fragments = ["test", "string"]
    one_of_fragments = ["is", "a"]
    result = path_selection_service.string_fragments_in_string(
        target_string, mandatory_fragments, one_of_fragments
    )
    assert result is False

    # Case none of the one of fragments exist
    target_string = "This is a test string"
    mandatory_fragments = ["test", "string"]
    one_of_fragments = ["not", "found"]
    result = path_selection_service.string_fragments_in_string(
        target_string, mandatory_fragments, one_of_fragments
    )
    assert result is False

    # Case empty mandatory fragments
    target_string = "This is a test string"
    mandatory_fragments = []
    one_of_fragments = ["is", "a"]
    result = path_selection_service.string_fragments_in_string(
        target_string, mandatory_fragments, one_of_fragments
    )
    assert result is True

    # Case empty one of fragments
    target_string = "This is a test string"
    mandatory_fragments = ["test", "string"]
    one_of_fragments = []
    result = path_selection_service.string_fragments_in_string(
        target_string, mandatory_fragments, one_of_fragments
    )
    assert result is False


def test_detect_marked_checkbox(path_selection_service):
    # Test a marked checkbox
    unmarked_checkbox_path = "/function/tests/checkbox_images/checkbox_x.jpg"
    assert path_selection_service.detect_marked_checkbox(unmarked_checkbox_path) is True

    # Test an unmarked checkbox
    marked_checkbox_path = "/function/tests/checkbox_images/checkbox_blank.jpg"
    assert path_selection_service.detect_marked_checkbox(marked_checkbox_path) is False

    # Test a marked grey checkbox
    unmarked_checkbox_path = "/function/tests/checkbox_images/checkbox_tick_grey.jpg"
    assert path_selection_service.detect_marked_checkbox(unmarked_checkbox_path) is True

    # Test an unmarked checkbox
    unmarked_checkbox_path = (
        "/function/tests/checkbox_images/checkbox_tick_grey_blank.jpg"
    )
    assert (
        path_selection_service.detect_marked_checkbox(unmarked_checkbox_path) is False
    )
