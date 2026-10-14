from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "ai-coo-frontend/src/pages/legal/PrivacyPolicy.tsx"


def test_public_privacy_policy_discloses_google_data_use_retention_and_controls():
    source = re.sub(r"\s+", " ", POLICY.read_text())

    required_disclosures = [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/calendar",
        "does not list, retrieve, or search inbox",
        "Calendar event data retrieved by these features is not sent to an AI service",
        "does not use Google Workspace API data to develop, improve, or train generalized",
        "https://developers.google.com/terms/api-services-user-data-policy",
        "including its Limited Use requirements",
        "encrypted before storage",
        "automatic WorkForge expiry period",
        "Disconnecting Gmail or Calendar",
        "does not revoke Google",
        "only member of the organization",
        "your user attribution removed",
    ]
    for disclosure in required_disclosures:
        assert disclosure in source

    for unsupported_or_model_specific_claim in (
        "Google Gemini",
        "Gemini API",
        "Paid Services",
        "Unpaid Services",
        "WorkForge&apos;s code does not determine",
        "Check the deployed provider account",
        "before relying on a no-training representation",
    ):
        assert unsupported_or_model_specific_claim not in source


def test_privacy_policy_is_on_the_public_route_and_linked_from_homepage():
    app = (ROOT / "ai-coo-frontend/src/App.tsx").read_text()
    client = (ROOT / "ai-coo-frontend/src/api/client.ts").read_text()
    home = (ROOT / "ai-coo-frontend/src/pages/home/Home.tsx").read_text()

    for route in ("privacy", "security", "terms"):
        assert f'path="/{route}"' in app
        assert f"'/{route}'" in client
        assert f'to="/{route}"' in home


def test_security_and_terms_match_google_disconnect_and_deletion_behavior():
    security = re.sub(r"\s+", " ", (ROOT / "ai-coo-frontend/src/pages/legal/Security.tsx").read_text())
    terms = re.sub(r"\s+", " ", (ROOT / "ai-coo-frontend/src/pages/legal/TermsOfService.tsx").read_text())

    assert "does not revoke the grant in your Google Account" in security
    assert "When the account is the organization&apos;s only member" in security
    assert "When other members remain" in security
    assert "retains shared organization records and integration credentials" in security
    assert "does not revoke" in security
    assert "Gmail and Google Calendar" in terms
    assert "WorkForge does not read your Gmail inbox or messages" in terms
    assert "external AI service provider" in terms
    assert "Calendar event data retrieved by these features is not sent to an AI service" in terms
    assert "Google Gemini" not in terms


def test_calendar_summary_is_removed_from_frontend_service_and_page():
    calendar = (ROOT / "ai-coo-frontend/src/pages/calendar/Calendar.tsx").read_text()
    service = (ROOT / "ai-coo-frontend/src/services/calendar/real.ts").read_text()
    types = (ROOT / "ai-coo-frontend/src/services/calendar/types.ts").read_text()
    assert "Load AI summary" not in calendar
    assert "handleLoadSummary" not in calendar
    assert "/calendar/summary" not in service
    assert "getSummary" not in service + types + calendar
