from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_newsletter_html():
    return (FIXTURES_DIR / "sample_newsletter.html").read_text()
