from datetime import timedelta

from uber.automated_emails import AutomatedEmailFixture, ArtShowAppEmailFixture, StopsEmailFixture
from uber.config import c
from uber.models import Attendee, AutomatedEmail
from uber.utils import before, days_before, days_after

ArtShowAppEmailFixture(
    'Preparing for the {EVENT_NAME} Art Show',
    'art_show/precon.html',
    lambda a: a.status == c.APPROVED,
    ident='art_show_precon')

AutomatedEmail.email_overrides.extend([
    ('art_show_confirm', 'subject', f"OFFICIAL Anthrocon Art Show reservation acknowledgement"),
    ('art_show_confirm', 'needs_approval', False),
    ('art_show_approved', 'subject', f"OFFICIAL Anthrocon Art Show reservation confirmation")])