from datetime import timedelta

from uber.automated_emails import AutomatedEmailFixture, ArtShowAppEmailFixture, StopsEmailFixture
from uber.config import c
from uber.models import Attendee, AutomatedEmail
from uber.utils import before, days_before, days_after

ArtShowAppEmailFixture(
    'Your {EVENT_NAME} Art Show Reservation',
    'art_show/import.html',
    lambda a: a.created <= c.ART_SHOW_REG_START,
    ident='art_show_import')