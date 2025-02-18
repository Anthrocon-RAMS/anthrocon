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
        MenuItem(name='Square Bidder Export', href='../anthrocon/square_bidder_export'),
        MenuItem(name='Square Piece Export', href='../anthrocon/square_piece_export'),
    ])
)

c.ART_SHOW_DELIVERY_OPTS = [(key, val) for key, val in c.ART_SHOW_DELIVERY_OPTS if key != c.BY_MAIL]
request_order = [c.ELECTRICITY, c.WIDE_ART, c.TALL_ART, c.FLOOR_SPACE, c.NEIGHBOR_REQUEST, c.MOVING]
c.ARTIST_SPECIAL_REQUEST_OPTS.sort(key=lambda x: request_order.index(x[0]))