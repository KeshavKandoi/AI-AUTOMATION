"""
Unit tests for job_hunter.platforms.yc_jobs._parse_work_mode().

Covers explicit-signal-only remote detection across YC's slash-separated
multi-location format, including the false-negative cases found during
live testing (Remote appearing in a non-first segment).
"""
from job_hunter.platforms.yc_jobs import _parse_work_mode


def test_remote_at_start():
    assert _parse_work_mode("Remote") == "Remote"


def test_remote_with_region_suffix():
    assert _parse_work_mode("Remote (US)") == "Remote"


def test_remote_only():
    assert _parse_work_mode("Remote only") == "Remote"


def test_fully_remote():
    assert _parse_work_mode("Fully remote") == "Remote"


def test_remote_at_end_of_multi_location():
    assert _parse_work_mode("San Francisco, CA, US / Remote") == "Remote"


def test_remote_in_middle_segment():
    assert _parse_work_mode("San Francisco, CA, US / SG / Remote (US)") == "Remote"


def test_remote_last_of_three_segments():
    assert _parse_work_mode(
        "Bengaluru, KA, IN / Bengaluru, Karnataka, IN / Remote"
    ) == "Remote"


def test_remote_at_start_of_multi_location():
    assert _parse_work_mode("Remote / San Francisco, CA, US") == "Remote"


def test_multiple_cities_no_remote_stays_null():
    assert _parse_work_mode("San Francisco, CA, US / New York, NY, US") is None


def test_single_city_stays_null():
    assert _parse_work_mode("San Francisco, CA, US") is None


def test_worldwide_is_not_inferred_as_remote():
    assert _parse_work_mode("Worldwide") is None


def test_none_location_stays_null():
    assert _parse_work_mode(None) is None


def test_empty_string_stays_null():
    assert _parse_work_mode("") is None
