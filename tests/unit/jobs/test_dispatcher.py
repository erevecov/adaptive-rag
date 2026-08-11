"""Dispatcher queue rotation and advisory-lock identity."""

from adaptive_rag.jobs.dispatcher import advisory_lock_id


def test_advisory_lock_id_is_stable_namespaced_and_signed() -> None:
    first = advisory_lock_id("handler", "echo", "1")

    assert first == advisory_lock_id("handler", "echo", "1")
    assert first != advisory_lock_id("key", "echo", "1")
    assert -(2**63) <= first < 2**63
