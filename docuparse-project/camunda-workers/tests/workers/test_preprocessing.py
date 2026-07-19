from workers.preprocessing import _preprocess_image


async def test_preprocess_image_increments_retry_count_from_zero():
    result = await _preprocess_image(document_id="doc-1", ocr_retry_count=0)

    assert result["ocr_retry_count"] == 1


async def test_preprocess_image_increments_retry_count_from_two():
    result = await _preprocess_image(document_id="doc-1", ocr_retry_count=2)

    assert result["ocr_retry_count"] == 3


async def test_preprocess_image_defaults_retry_count_to_zero_then_increments():
    result = await _preprocess_image(document_id="doc-1")

    assert result["ocr_retry_count"] == 1
