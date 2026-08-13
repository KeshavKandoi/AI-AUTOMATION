"""
Unit tests for job_hunter.platforms.greenhouse._extract_work_mode().

Confirms extraction uses ONLY the structured location.name field and
never scans free-text descriptions -- a real false positive was found
during live testing where a job's description contained "This role can
either be fully remote depending on which US state you live in, or
based in our New York City office" (a conditional arrangement, not an
unconditional Remote statement), which a description-scanning approach
incorrectly classified as Remote.
"""
from job_hunter.platforms.greenhouse import _extract_work_mode


def test_explicit_remote_location():
    assert _extract_work_mode("Remote") == "Remote"


def test_remote_with_region():
    assert _extract_work_mode("Remote - USA") == "Remote"


def test_remote_select_locations():
    assert _extract_work_mode("Remote - US: Select locations") == "Remote"


def test_hybrid_location():
    assert _extract_work_mode("Hybrid - Austin, TX") == "Hybrid"


def test_onsite_location():
    assert _extract_work_mode("On-site - San Francisco") == "On-site"


def test_in_office_location():
    assert _extract_work_mode("In-office - New York") == "On-site"


def test_generic_country_stays_null():
    assert _extract_work_mode("United States") is None


def test_worldwide_stays_null():
    assert _extract_work_mode("Worldwide") is None


def test_anywhere_stays_null():
    assert _extract_work_mode("Anywhere") is None


def test_bare_city_stays_null():
    assert _extract_work_mode("New York City") is None


def test_multi_city_list_stays_null():
    assert _extract_work_mode("SF, NYC, SEA, CHI") is None


def test_function_no_longer_accepts_description_param():
    """Regression guard: _extract_work_mode must only take location --
    if a description param is ever re-added, this test signature will
    force a deliberate review rather than silently reintroducing the
    description-scanning false-positive risk."""
    import inspect
    sig = inspect.signature(_extract_work_mode)
    assert list(sig.parameters.keys()) == ["location"]
