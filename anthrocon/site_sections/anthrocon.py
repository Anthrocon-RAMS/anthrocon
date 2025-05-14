import os
import json
import shlex
import time
import sys
import subprocess
import traceback
import csv
import random
import six
import pycountry
import cherrypy
import threading
from collections import defaultdict
from datetime import datetime

from sqlalchemy.dialects.postgresql.json import JSONB
from sqlalchemy.exc import IntegrityError, NoResultFound
from pockets.autolog import log
from pytz import UTC
from sqlalchemy.types import Date, Boolean, Integer
from sqlalchemy import text

from uber.badge_funcs import badge_consistency_check
from uber.config import c
from uber.decorators import all_renderable, csv_file, public, site_mappable, xlsx_file
from uber.models import Attendee, ArtShowApplication, ArtShowBidder, ArtShowPiece, Choice, MultiChoice, Session, UTCDateTime
from uber.tasks.health import ping


def _handle_preferred_name(row, model_instances):
    orig_preferred_name = row.pop('attendee_preferred_name', None)
    orig_first_name = row.pop('attendee_first_name', None)
    orig_last_name = row.pop('attendee_last_name', None)

    preferred_name_split = orig_preferred_name.rsplit(' ', 1)
    if len(preferred_name_split) > 1:
        preferred_last_name = preferred_name_split[1]
        model_instances['attendee'].first_name = preferred_name_split[0]
        if preferred_last_name == orig_last_name:
            model_instances['attendee'].last_name = orig_last_name
            model_instances['attendee'].legal_name = orig_first_name
        else:
            model_instances['attendee'].last_name = preferred_name_split[1]
            model_instances['attendee'].legal_name = orig_first_name + " " + orig_last_name
    else:
        model_instances['attendee'].legal_name = orig_first_name
        model_instances['attendee'].last_name = orig_last_name
        model_instances['attendee'].first_name = orig_preferred_name


@all_renderable()
class Root:
    @csv_file
    def square_bidder_export(self, out, session):
        out.writerow(["First Name", "Last Name", "Company Name", "Email Address", "Phone Number",
                      "Street Address 1", "Street Address 2", "City", "State", "Postal Code",
                      "Reference ID", "Birthday", "Email Subscription Status"])
        for bidder in session.query(ArtShowBidder).all():
            attendee = bidder.attendee
            out.writerow([
                attendee.first_name, attendee.last_name, "", attendee.email,
                attendee.cellphone, attendee.address1, attendee.address2,
                attendee.city, attendee.region, attendee.zip_code,
                "BN" + bidder.bidder_num[2:], "", ""
            ])

    @xlsx_file
    def square_piece_export(self, out, session):
        out.writerow("")
        out.writerow(["Token", "Item Name", "Variation Name", "SKU", "Description", "Category",
                      "SEO Title", "SEO Description", "Permalink", "Weight (lb)", "Price",
                      "Online Sale Price", "Sellable", "Stockable", "Skip Detail Screen in POS",
                      "Option Name 1", "Option Value 1", "Enabled ART SHOW", "Current Quantity ART SHOW",
                      "New Quantity ART SHOW", "Stock Alert Enabled ART SHOW", "Stock Alert Count ART SHOW",
                      "Price ART SHOW", "Enabled CON STORE", "Current Quantity CON STORE", "New Quantity CON STORE",
                      "Stock Alert Enabled CON STORE", "Stock Alert Count CON STORE", "Price CON STORE",
                      "Enabled REGISTRATION", "Current Quantity REGISTRATION", "New Quantity REGISTRATION",
                      "Stock Alert Enabled REGISTRATION", "Stock Alert Count REGISTRATION", "Price REGISTRATION"])
        for piece in session.query(ArtShowPiece).join(ArtShowApplication).all():
            square_piece_id = piece.artist_and_piece_id.replace('-', '')
            out.writerow([
                "", f"{square_piece_id} {piece.name}", "Regular", square_piece_id, piece.app_display_name, "Department",
                "", "", "", "", "variable", "", "", "", "Y", "", "", "Y", "", "", "", "", "", "N", "", "", "", "", "",
                "N", "", "", "", "", ""
            ])

    @csv_file
    def art_show_export(self, out, session):
        app_fields = ['import_id', 'created', 'address1', 'address2', 'city', 'region', 'zip_code', 'country',
                      'website', 'status', 'artist_id', 'banner_name', 'artist_id_ad', 'banner_name_ad',
                      'panels', 'tables', 'panels_ad', 'tables_ad', 'locations', 'agent_notes', 'check_payable',
                      'payout_method', 'payout_method_text', 'check_in_notes', 'contact_at_con', 'admin_notes',
                      'photography_ok', 'special_requests', 'special_requests_text', 'requested_more_space']
        attendee_fields = ['last_name', 'first_name', 'legal_name', 'email', 'cellphone']

        header_row = []
        header_row.extend(['attendee_' + field_name for field_name in attendee_fields])
        header_row.extend(['app_' + field_name for field_name in app_fields])
        out.writerow(header_row)

        for app in session.query(ArtShowApplication).outerjoin(ArtShowApplication.attendee):
            row = []
            if app.attendee:
                row.extend([getattr(app.attendee, key, '') for key in attendee_fields])
            else:
                row.extend(['N/A', 'N/A', '', 'N/A', ''])

            for key in app_fields:
                if key == 'import_id':
                    row.append(app.id)
                else:
                    col = getattr(ArtShowApplication, key)

                    if isinstance(col.type, Choice):
                        row.append(getattr(app, col.name + '_label'))
                    elif isinstance(col.type, MultiChoice):
                        row.append(' / '.join(getattr(app, col.name + '_labels')))
                    elif isinstance(col.type, UTCDateTime):
                        val = getattr(app, col.name)
                        row.append(val.strftime('%Y-%m-%d %H:%M:%S') if val else '')
                    elif isinstance(col.type, JSONB):
                        row.append(json.dumps(getattr(app, col.name)))
                    else:
                        row.append(getattr(app, col.name))
            out.writerow(row)

    def art_show_import(self, message='', all_instances=[]):
        return {
            'message': message,
            'models_imported': [x for xs in all_instances for x in xs]
        }

    def import_art_show_models(self, session, model_import):
        model_dict = {
            'attendee': Attendee,
            'app': ArtShowApplication,
        }
        col_dict = {}
        state_lookup = {region.code.removeprefix('US-'): region.name for region in list(
            pycountry.subdivisions.get(country_code='US'))}
        province_lookup = {region.code.removeprefix('CA-'): region.name for region in list(
            pycountry.subdivisions.get(country_code='CA'))}

        for key, model in model_dict.items():
            col_dict[key] = {col.name: getattr(model, col.name) for col in model.__table__.columns}
        message = ''

        result = csv.DictReader(model_import.file.read().decode('utf-8').split('\n'))
        id_lists = defaultdict(list)

        for row in result:
            import_ids = {}
            model_instances = {}
            colnames = {}

            for key in model_dict.keys():
                if key + '_import_id' in row:
                    import_ids[key] = row.pop(key + '_import_id')
                    try:
                        model_instances[key] = session.query(model_dict[key]).filter(
                            model_dict[key].external_id == {'art_show_import': import_ids[key]}).one()
                    except NoResultFound:
                        try:
                            model_instances[key] = session.query(model_dict[key]
                                                                 ).filter(model_dict[key].id == import_ids[key]).one()
                        except NoResultFound:
                            pass
                    except Exception as e:
                        log.error(str(e))
                        session.rollback()
                        return self.art_show_import(str(e))
            
            if model_instances.get('app'):
                model_instances['attendee'] = model_instances['app'].attendee
            elif model_instances.get('attendee'):
                model_instances['app'] = ArtShowApplication(
                    external_id = {'art_show_import': import_ids['app']}
                )
            else:
                model_instances['app'] = ArtShowApplication(
                    external_id = {'art_show_import': import_ids['app']}
                )
                model_instances['attendee'] = Attendee()
                model_instances['attendee'].placeholder = True
                model_instances['attendee'].badge_status = c.NOT_ATTENDING

            model_instances['app'].attendee = model_instances['attendee']
            model_instances['app'].last_synced['art_show_import'] = datetime.now(UTC).isoformat()
            model_instances['attendee'].last_synced['art_show_import'] = datetime.now(UTC).isoformat()

            # Swap the preferred and first names where appropriate
            if row.get('attendee_preferred_name', None):
                _handle_preferred_name(row, model_instances)

            # Process country/state
            country = row.pop('app_country', None)

            if country == 'USA':
                model_instances['app'].country = "United States"
                state = row.pop('app_region')
                model_instances['app'].region = state_lookup.get(state, '')
            elif country and country.lower() == 'CANADA'.lower():
                model_instances['app'].country = country.title()
                province = row.pop('app_region')
                model_instances['app'].region = province_lookup.get(province, '')
            elif country:
                model_instances['app'].country = country.title()

            for key in model_dict.keys():
                session.add(model_instances[key])
                colnames[key] = [k for k in row.keys() if k.startswith(key)]

            for key in model_dict.keys():
                for colname in colnames[key]:
                    col = col_dict[key][colname.removeprefix(key + "_")]
                    if row[colname]:
                        setattr(model_instances[key], colname.removeprefix(key + "_"), model_instances[key].coerce_column_data(col, row[colname]))

            for key in model_dict.keys():
                id_lists[key].append(model_instances[key].id)
            
            log.error(model_instances['app'].external_id)

        try:
            session.commit()
        except Exception as e:
            log.error('ImportError', exc_info=True)
            session.rollback()
            message = str(e)

        all_instances = []
        if len(id_lists) > 0:
            for key, model in model_dict.items():
                all_instances.append(session.query(model).filter(model.id.in_(id_lists[key])).all())

        return self.art_show_import(message, all_instances)