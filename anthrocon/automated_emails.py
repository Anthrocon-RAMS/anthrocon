from datetime import timedelta

from uber.automated_emails import AutomatedEmailFixture, MarketplaceEmailFixture, StopsEmailFixture
from uber.config import c
from uber.models import Attendee, AutomatedEmail
from uber.utils import before, days_before, days_after

# ArtShowAppEmailFixture(
#     Attendee,
#     '{EVENT_NAME} hospitality suite information',
#     'guest_food_info.txt',
#     lambda a: a.badge_type == c.GUEST_BADGE,
#     ident='anthrocon_guest_food_info')