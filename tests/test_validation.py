from app.validation import generate_synthetic_batch


def test_generate_synthetic_batch_has_50_plus_records():
    batch = generate_synthetic_batch(60)

    assert len(batch["payment"]) == 60
    assert len(batch["bank"]) == 60
    assert len(batch["ledger"]) == 60
    assert sum(1 for item in batch["payment"] if item["status"] == "SUCCESS") >= 40
