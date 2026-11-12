from map_qa import model as m


def test_checks_order():
    assert m.CHECK_ORDER == ("C1", "C2", "C3", "C4", "C4-manual")


def test_speed_reason_codes_closed():  # ADR-001 D-101
    assert m.SPEED_REASONS == {
        "zone",
        "none",
        "signals",
        "multi_value",
        "unparsable",
        "conditional",
    }


def test_not_comparable_codes():
    assert {
        "not_numeric",
        "conditional",
        "partial_segment",
        "partial_source",
        "direction_unknown",
        "variable",
        "multiple_rules",
        "unknown_family",
        "outside_snapshot",
    } == m.NOT_COMPARABLE_REASONS


def test_flags():  # AC-16
    assert len(m.FILE_FLAGS) == 9
    assert m.OWN_FLAGS == ("link_recheck_mismatch", "restricted_access", "grade_separated_nearby")


def test_resolution_states():  # AC-22e
    assert m.RESOLVED_BY == ("decision_model", "general_llm", "human_pending", "not_run")
    assert m.MANUAL_REASONS == (
        "below_threshold",
        "unreadable",
        "model_unavailable",
        "budget_exhausted",
    )


def test_input_error_message():
    err = m.InputError("photos.csv", "hash_mismatch")
    assert err.file == "photos.csv" and err.reason == "hash_mismatch"
    assert "photos.csv" in str(err)


def test_candidate_defaults():
    c = m.Candidate(check="C1", reason_code="missing_surface", osm_id=5)
    assert c.file_flags == () and c.own_flags == ()
    assert c.uncertain_link is False
    assert c.segment_id == ""
