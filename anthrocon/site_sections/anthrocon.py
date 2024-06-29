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
from uber.decorators import all_renderable, csv_file, public, site_mappable
from uber.models import Attendee, ArtShowApplication, Session, UTCDateTime
from uber.tasks.health import ping


@all_renderable()
class Root:
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
            orig_first_name = row.pop('attendee_first_name', None)
            orig_last_name = row.pop('attendee_last_name', None)
            orig_preferred_name = row.pop('attendee_preferred_name', None)

            if orig_preferred_name:
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
            else:
                model_instances['attendee'].first_name = orig_first_name
                model_instances['attendee'].last_name = orig_last_name

            # Process country/state
            country = row.pop('app_country')

            if country == 'USA':
                model_instances['app'].country = "United States"
                state = row.pop('app_region')
                model_instances['app'].region = state_lookup[state]
            else:
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