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
import pypsutil
import cherrypy
import threading
from collections import defaultdict
from datetime import datetime

from sqlalchemy.dialects.postgresql.json import JSONB
from pockets.autolog import log
from pytz import UTC
from sqlalchemy.types import Date, Boolean, Integer
from sqlalchemy import text

from uber.badge_funcs import badge_consistency_check
from uber.decorators import all_renderable, csv_file, public, site_mappable
from uber.models import Attendee, ArtShowApplication, Session, UTCDateTime
from uber.tasks.health import ping


class Root:
    def art_show_import(self, message='', all_instances=None):
        return {
            'message': message,
            'attendees': all_instances
        }

    def import_art_show_models(self, session, model_import):
        model_dict = {
            'attendee': Attendee,
            'app': ArtShowApplication,
        }
        col_dict = {}

        for key, model in model_dict.items():
            col_dict[key] = {col.name: getattr(model, col.name) for col in model.__table__.columns}
        message = ''

        result = csv.DictReader(model_import.file.read().decode('utf-8').split('\n'))
        id_lists = defaultdict(list)

        for row in result:
            model_instances = {}
            colnames = {}

            for key in model_dict.keys():
                if key + '_import_id' in row:
                    import_id = row.pop(key + '_import_id')
                    try:
                        model_instances[key] = getattr(session, model_dict[key])(import_id, allow_invalid=True)
                    except Exception:
                        session.rollback()
            
            if model_instances.get('app'):
                model_instances['attendee'] = model_instances['app'].attendee
            elif model_instances.get('attendee'):
                model_instances['app'] = ArtShowApplication()
                model_instances['app'].attendee = model_instances['attendee']
            else:
                model_instances['app'] = ArtShowApplication()
                model_instances['attendee'] = Attendee()

            for key in model_dict.keys():
                colnames[key] = [key for key in row.keys() if key.startswith(key)]

            for key in model_dict.keys():
                for colname in colnames[key]:
                    col = col_dict[key][colname.removeprefix(key + "_")]
                    setattr(model_instances[key], col, model_instances[key].coerce_column_data(col, row[colname]))

            for key in model_dict.keys():
                id_lists[key].append(model_instances[key].id)

        try:
            session.commit()
        except Exception:
            log.error('ImportError', exc_info=True)
            session.rollback()
            message = 'Import unsuccessful'

        all_instances = []
        if len(id_lists) > 0:
            for key, model in model_dict.items():
                all_instances.append(session.query(model).filter(model.id.in_(id_lists[key])).all())

        return self.art_show_import(message, all_instances)