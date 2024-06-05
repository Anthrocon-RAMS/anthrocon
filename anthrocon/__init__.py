from os.path import join
from pathlib import Path

from uber.config import c, parse_config
from uber.jinja import template_overrides
from uber.utils import mount_site_sections, static_overrides

from anthrocon._version import __version__  # noqa: F401


config = parse_config("anthrocon", Path(__file__).parents[0])
c.include_plugin_config(config)
mount_site_sections(config['module_root'])
static_overrides(join(config['module_root'], 'static'))
template_overrides(join(config['module_root'], 'templates'))


# These need to come last so they can make use of config properties
from anthrocon.automated_emails import *  # noqa: F401,E402,F403
from anthrocon.models import *  # noqa: F401,E402,F403
