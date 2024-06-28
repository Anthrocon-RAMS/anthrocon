from os.path import join
from pathlib import Path

from uber.config import c, Config, dynamic, parse_config, request_cached_property
from uber.menu import MenuItem
from uber.models import Attendee, Session

from ._version import __version__  # noqa: F401

config = parse_config("anthrocon", Path(__file__).parents[0])
c.include_plugin_config(config)

c.MENU.append_menu_item(
    MenuItem(name='Anthrocon', submenu=[
        MenuItem(name='Art Show Import', href='../anthrocon/art_show_import'),
    ])
)