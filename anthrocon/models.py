from uber.models import Session
from uber.models.types import DefaultColumn as Column, MultiChoice
from uber.config import c
from residue import CoerceUTF8 as UnicodeText


@Session.model_mixin
class ArtShowApplication:
    agent_notes = Column(UnicodeText)