from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest

from app.utility.custom_logging import LogMessageDetails
from app.utility.extraction_service import (
    ExtractionService,
    FilteredMetastore,
    MatchingMetaToImages,
)
from form_tools.form_meta.form_meta import FormPage
from form_tools.form_operators import FormOperator


@pytest.fixture
def recovery(tmp_path, monkeypatch):
    image = np.full((100, 100, 3), 255, dtype=np.uint8)
    source = tmp_path / "source.png"
    assert cv2.imwrite(str(source), image)
    assert cv2.imwrite(str(tmp_path / "page_1.png"), image)
    page = FormPage(identifier="Continuation", page_number=1)
    meta = SimpleNamespace(
        form_pages=[page], form_fields=[], form_template=str(tmp_path)
    )
    service = ExtractionService(
        "extraction", "test", str(tmp_path), LogMessageDetails()
    )
    monkeypatch.setattr(
        service, "get_meta_page_text", lambda page: "Continuation verified text"
    )
    monkeypatch.setattr(
        "app.utility.extraction_service.get_text_from_image_file",
        lambda paths: ["Continuation verified text"],
    )
    align = MagicMock(return_value=image)
    operator = SimpleNamespace(
        form_page_operator=SimpleNamespace(align_image_to_template=align)
    )
    return service, operator, {"lpc": meta}, str(source), align


def test_recovery_verifies_ocr_and_retains_original(recovery):
    service, operator, metas, source, align = recovery
    result = service.recover_ocr_matches([source], operator, metas)
    assert result[0].meta_id == "lpc"
    assert np.array_equal(result[0].image_page_map[1][0], cv2.imread(source))
    assert align.call_count == 1
    assert "Template-assisted OCR recovered" in service.info_msg.matched_templates[0]


@pytest.mark.parametrize(
    "text", ["unrelated correspondence", "Continuation unrelated", ""]
)
def test_recovery_requires_identifier_and_similarity(recovery, monkeypatch, text):
    service, operator, metas, source, _ = recovery
    monkeypatch.setattr(
        "app.utility.extraction_service.get_text_from_image_file", lambda paths: [text]
    )
    assert service.recover_ocr_matches([source], operator, metas) == []


def test_recovery_rejects_ambiguous_templates(recovery, caplog):
    service, operator, metas, source, _ = recovery
    metas["other"] = metas["lpc"]
    assert service.recover_ocr_matches([source], operator, metas) == []
    assert "Ambiguous" in caplog.text


def test_recovery_requires_a_clear_margin(recovery, monkeypatch):
    service, operator, metas, source, _ = recovery
    metas["other"] = metas["lpc"]
    scores = iter([0.9, 0.8])
    monkeypatch.setattr(service, "similarity_score", lambda *args: next(scores))
    result = service.recover_ocr_matches([source], operator, metas)
    assert result[0].meta_id == "lpc"


def test_recovery_candidate_limit(recovery, caplog):
    service, operator, metas, source, align = recovery
    metas = {f"meta_{i}": metas["lpc"] for i in range(13)}
    assert service.recover_ocr_matches([source], operator, metas) == []
    align.assert_not_called()
    assert "candidate or time budget" in caplog.text


def test_recovery_does_not_hide_ocr_errors(recovery, monkeypatch):
    service, operator, metas, source, _ = recovery

    def failed_ocr(paths):
        raise OSError("OCR unavailable")

    monkeypatch.setattr(
        "app.utility.extraction_service.get_text_from_image_file", failed_ocr
    )
    with pytest.raises(OSError, match="OCR unavailable"):
        service.recover_ocr_matches([source], operator, metas)


def test_recovery_rejects_unsafe_alignment(recovery, caplog):
    service, operator, metas, source, align = recovery
    align.side_effect = RuntimeError("Unsafe geometry")
    assert service.recover_ocr_matches([source], operator, metas) == []


def test_recovery_budget_does_not_return_partial_success(recovery, caplog):
    service, operator, metas, source, align = recovery
    assert service.recover_ocr_matches([source] * 13, operator, metas) == []
    assert align.call_count == 12
    assert "work budget" in caplog.text
    assert service.info_msg.matched_templates == []


def test_recovery_deadline(recovery, monkeypatch, caplog):
    service, operator, metas, source, align = recovery
    clock = iter([0, 0, 31])
    monkeypatch.setattr(
        "app.utility.extraction_service.time.monotonic", lambda: next(clock)
    )
    assert service.recover_ocr_matches([source], operator, metas) == []
    align.assert_not_called()
    assert "work budget" in caplog.text


def test_recovery_does_not_start_ocr_after_alignment_exhausts_budget(
    recovery, monkeypatch, caplog
):
    service, operator, metas, source, align = recovery
    clock = iter([0, 0, 0, 31])
    monkeypatch.setattr(
        "app.utility.extraction_service.time.monotonic", lambda: next(clock)
    )
    ocr = MagicMock()
    monkeypatch.setattr("app.utility.extraction_service.get_text_from_image_file", ocr)
    assert service.recover_ocr_matches([source], operator, metas) == []
    align.assert_called_once()
    ocr.assert_not_called()
    assert "time budget" in caplog.text


def test_equivalent_continuation_pages_are_not_ambiguous(recovery):
    service, operator, metas, source, align = recovery
    metas["lpc"].form_pages.append(FormPage(identifier="Continuation", page_number=2))
    result = service.recover_ocr_matches([source, source], operator, metas)
    assert set(result[0].image_page_map) == {1, 2}
    assert align.call_count == 2


def test_inline_recovery_preserves_repeated_sheets(recovery):
    service, operator, metas, source, _ = recovery
    result = service.recover_ocr_matches([source, source], operator, metas, True)
    assert len(result) == 2
    assert all(set(match.image_page_map) == {1} for match in result)


@pytest.mark.parametrize("matched", [True, False])
def test_ocr_recovery_only_runs_after_identification_failure(
    recovery, monkeypatch, matched
):
    service, operator, metas, source, _ = recovery
    match = MatchingMetaToImages("lpc", {1: [cv2.imread(source)]} if matched else {})
    monkeypatch.setattr(service, "mixed_mode_page_identifier", lambda **kwargs: [match])
    monkeypatch.setattr(service, "mask_images", lambda *args: [source])
    monkeypatch.setattr(service, "smart_threshold_images", lambda *args: [source])
    recovery_mock = MagicMock(return_value=[])
    monkeypatch.setattr(service, "recover_ocr_matches", recovery_mock)
    service.get_ocr_matches([source], operator, FilteredMetastore(metas, {}), source)
    assert recovery_mock.call_count == (0 if matched else 1)


def test_inline_ocr_failure_uses_recovery(recovery, monkeypatch):
    service, operator, metas, source, _ = recovery
    main = MatchingMetaToImages("lp1f", {1: [cv2.imread(source)]})
    monkeypatch.setattr(
        service,
        "mixed_mode_page_identifier",
        lambda **kwargs: [] if kwargs["inline_continuation"] else [main],
    )
    monkeypatch.setattr(service, "mask_images", lambda *args: [source])
    monkeypatch.setattr(service, "smart_threshold_images", lambda *args: [source])
    monkeypatch.setattr(
        service,
        "filter_metastore_based_on_meta_id",
        lambda *args: FilteredMetastore({}, metas),
    )
    recovery_mock = MagicMock(return_value=[])
    monkeypatch.setattr(service, "recover_ocr_matches", recovery_mock)
    result = service.get_ocr_matches(
        [source], operator, FilteredMetastore(metas, {}), source
    )
    assert result is main
    recovery_mock.assert_called_once_with(
        [source], operator, metas, inline_continuation=True
    )


@pytest.mark.parametrize("perspective", [False, True])
def test_distorted_local_lpc_recovery(tmp_path, perspective):
    from pdf2image import convert_from_path
    from app.utility.ocr import get_text_from_image_file
    from form_tools.form_operators.bounding_box_operator import BoundingBoxOperator

    root = Path(__file__).resolve().parents[4]
    source = (
        root
        / "local-services/localstack-request-handler/s3-uploads/700000059449_20250320164301.311702_LPC.pdf"
    )
    if not source.exists():
        pytest.skip("Local upload fixtures are required")
    page = convert_from_path(
        source, first_page=2, last_page=2, fmt="jpeg", output_folder=str(tmp_path)
    )[0]
    page.save(tmp_path / "source.jpg", "JPEG")
    image = cv2.imread(str(tmp_path / "source.jpg"))
    h, w = image.shape[:2]
    transform = cv2.getPerspectiveTransform(
        np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]]),
        np.float32(
            [
                [0.12 * w, 0.04 * h],
                [0.91 * w, 0.13 * h],
                [0.98 * w, 0.94 * h],
                [0.03 * w, 0.86 * h],
            ]
        ),
    )
    if perspective:
        warped = cv2.warpPerspective(
            image, transform, (w, h), borderValue=(255, 255, 255)
        )
    else:
        transform = cv2.getRotationMatrix2D((w / 2, h / 2), 12, 0.95)
        transform[:, 2] += [15, -10]
        warped = cv2.warpAffine(image, transform, (w, h), borderValue=(255, 255, 255))
    path = tmp_path / "warped.png"
    assert cv2.imwrite(str(path), warped)
    service = ExtractionService(
        str(root / "lambdas/image_processor/extraction"),
        "test",
        str(tmp_path),
        LogMessageDetails(),
    )
    operator = FormOperator.create_from_config(
        f"{service.extraction_folder_path}/opg-config.yaml"
    )
    service.complete_meta_store = operator.form_meta_store(
        f"{service.extraction_folder_path}/metadata"
    )
    for meta in service.complete_meta_store.values():
        meta.form_template = str(root / "lambdas/image_processor" / meta.form_template)
    metas = service.filter_metastore_based_on_template(
        service.complete_meta_store, "LPC"
    )
    raw_text = get_text_from_image_file([str(path)])[0]
    reference = service.get_meta_page_text(
        metas.filtered_metastore["lpc"].form_pages[0]
    )
    assert service.similarity_score(reference, raw_text) < 0.7
    cv2.setRNGSeed(42)
    match = service.get_ocr_matches([str(path)], operator, metas, str(path))
    if perspective:
        assert match.size == 0
        return
    assert match.meta_id == "lpc"
    assert set(match.image_page_map) == {1}
    cv2.setRNGSeed(42)
    aligned = operator.align_images_to_template(
        match.image_page_map, metas.filtered_metastore["lpc"]
    )
    field = next(
        f
        for f in metas.filtered_metastore["lpc"].form_fields
        if f.name == "continuation_sheet_p1"
    )
    crop = BoundingBoxOperator.crop_image_to_bb(aligned[1][0], field.bounding_box)
    assert crop.shape[:2] == (725, 1435)
    assert cv2.imwrite(str(tmp_path / "crop.png"), crop)
    assert "NOBODY" in get_text_from_image_file([str(tmp_path / "crop.png")])[0].upper()
    cv2.setRNGSeed(42)
    known_template = operator.align_images_to_template(
        {1: [warped]}, metas.filtered_metastore["lpc"]
    )[1][0]
    expected = BoundingBoxOperator.crop_image_to_bb(known_template, field.bounding_box)
    assert np.array_equal(crop, expected)
