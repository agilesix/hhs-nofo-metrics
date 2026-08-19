from __future__ import annotations

import hhs_nofo_metrics
import hhs_nofo_metrics.models as public_models
from hhs_nofo_metrics import list_adapters


def test_internal_sentence_inventory_is_not_public_api() -> None:
    assert not hasattr(hhs_nofo_metrics, "generate_draft_sentence_inventory")
    assert not hasattr(public_models, "DocumentEvidenceDraft")


def test_product_registers_supported_generic_source_adapters() -> None:
    adapters = list_adapters()

    assert [item["id"] for item in adapters] == [
        "hhs-pdf-adapter",
        "hhs-semantic-html-adapter",
        "hhs-tagged-pdf-adapter",
    ]
    assert adapters[0]["reference"].startswith("hhs-pdf-adapter@")
