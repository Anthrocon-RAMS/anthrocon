from os.path import join

from uber.jinja import template_overrides
from uber.utils import mount_site_sections, static_overrides
from .config import config
from anthrocon.automated_emails import *  # noqa: F401,E402,F403
from anthrocon.models import *  # noqa: F401,E402,F403


static_overrides(join(config['module_root'], 'static'))
template_overrides(join(config['module_root'], 'templates'))
mount_site_sections(config['module_root'])
