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
        "event titles and start and end times",
        "Google Gemini",
        "encrypted before storage",
        "automatic WorkForge expiry period",
        "Disconnecting Gmail or Calendar",
        "does not revoke Google",
        "only member of the organization",
        "your user attribution removed",
        "does not use Google Workspace data to develop, improve, or train generalized",
        "Unpaid Services",
        "Paid Services",
    ]
    for disclosure in required_disclosures:
        assert disclosure in source


def test_privacy_policy_is_on_the_public_route_and_linked_from_homepage():
    app = (ROOT / "ai-coo-frontend/src/App.tsx").read_text()
    client = (ROOT / "ai-coo-frontend/src/api/client.ts").read_text()
    home = (ROOT / "ai-coo-frontend/src/pages/home/Home.tsx").read_text()

    assert 'path="/privacy"' in app
    assert "'/privacy'" in client
    assert 'to="/privacy"' in home
