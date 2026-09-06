import uuid

import pytest

from app.models.models import ContentStatus, Show
from app.services.validation import run_validation


@pytest.mark.asyncio
async def test_validation_no_publishable_content(db_session):
    report = await run_validation(db_session)
    assert not report.ready
    assert any(issue.code == "NO_PUBLISHABLE_CONTENT" for issue in report.issues)

@pytest.mark.asyncio
async def test_validation_missing_section(db_session):
    show = Show(id=uuid.uuid4(), title="Test Show", slug="test-show", status=ContentStatus.PUBLISHED)
    db_session.add(show)
    await db_session.commit()

    report = await run_validation(db_session)
    assert not report.ready
    assert any(issue.code == "SHOW_MISSING_SECTION" for issue in report.issues)
