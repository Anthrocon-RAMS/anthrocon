from datetime import datetime

from os.path import join

from residue import CoerceUTF8 as UnicodeText
from sqlalchemy.types import Boolean, Date
from uber.api import AttendeeLookup
from uber.config import c, Config
from uber.decorators import cost_property, prereg_validation, presave_adjustment, validation
from uber.menu import MenuItem
from uber.models import ArtShowApplication, Attendee, DefaultColumn as Column, Session
from uber.model_checks import invalid_phone_number
from uber.jinja import template_overrides
from uber.utils import add_opt, mount_site_sections, static_overrides, localized_now


Attendee.required = [('first_name', 'First Name'),
                     ('last_name', 'Last Name'),
                     ('email', 'Email'),
                     ('cellphone', 'Phone #'),]


ArtShowApplication.required = [('zip_code', 'ZipCode'),
                               ('address1', 'Address Line 1'),
                               ('city', 'City'),
                               ('region', 'State/Region'),
                               ('country', 'Country'),]


@validation.Attendee
def cellphone_valid(attendee):
    if attendee.cellphone and invalid_phone_number(attendee.cellphone):
        return 'Your cellphone number was not a valid 10-digit US phone number. ' \
            'Please include a country code (e.g. +44) for international numbers.'


@validation.ArtShowBidder
def must_select_phone_type(bidder):
    if not bidder.phone_type:
        return "You must select whether your phone number is a mobile number or a landline."


@validation.ArtShowBidder
def must_acknowledge_pickup(bidder):
    if not bidder.pickup_time_acknowledged:
        return "You must acknowledge the time to pick up your won art on Sunday."
