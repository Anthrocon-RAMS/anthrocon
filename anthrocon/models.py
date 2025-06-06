from pockets import classproperty
from residue import CoerceUTF8 as UnicodeText
from sqlalchemy.types import Integer, Boolean

from uber.config import c
from uber.custom_tags import readable_join
from uber.decorators import presave_adjustment
from uber.models import Session
from uber.models.types import DefaultColumn as Column, Choice, MultiChoice
from uber.utils import get_static_file_path


@Session.model_mixin
class Attendee:
    regfox_id = Column(UnicodeText)


@Session.model_mixin
class ArtShowApplication:
    agent_notes = Column(UnicodeText)
    photography_ok = Column(Boolean, default=False)
    special_requests = Column(MultiChoice(c.ARTIST_SPECIAL_REQUEST_OPTS))
    special_requests_text = Column(UnicodeText)
    requested_more_space = Column(Boolean, default=False)
    payout_method_text = Column(UnicodeText)

    @property
    def editable(self):
        return self.status in [c.UNAPPROVED, c.WAITLISTED]

    @property
    def special_requests_repr(self):
        if not self.special_requests and not self.special_requests_text:
            return "None"
        
        text = ""
        if self.special_requests:
            text = readable_join(self.special_requests_labels)
            if self.special_requests_text:
                return text + f". Details/Other: {self.special_requests_text}"
            return text
        return f"Other: {self.special_requests_text}"


@Session.model_mixin
class ArtShowBidder:
    phone_type = Column(Choice(c.PHONE_TYPE_OPTS), default=c.MOBILE)
    share_email = Column(Boolean, default=False)
    share_address = Column(Boolean, default=False)
    pickup_time_acknowledged = Column(Boolean, default=False)

    @presave_adjustment
    def zfill_bidder_num(self):
        if not self.bidder_num:
            return
        base_bidder_num = ArtShowBidder.strip_bidder_num(self.bidder_num)
        self.bidder_num = self.bidder_num[:2].upper() + str(base_bidder_num).zfill(3)

    @classproperty
    def required_fields(cls):
        return {
            'badge_num': "badge number",
            'bidder_num': "bidder number",
            'badge_printed_name': "badge name or nickname",
            'first_name': "first name",
            'last_name': "last name",
            'email': "email address",
            'cellphone': "phone number",
        }


@Session.model_mixin
class ArtShowPiece:
    artist_name = Column(UnicodeText)

    @property
    def app_display_name(self):
        if self.artist_name:
            return self.artist_name

        if not self.app:
            return "???"

        if self.gallery == c.MATURE:
            return self.app.mature_display_name
        else:
            return self.app.display_name

    def print_bidsheet(self, pdf, sheet_num, normal_font_name, bold_font_name, set_fitted_font_size):
        xplus = yplus = 0

        if sheet_num in [1, 3]:
            xplus = 306
        if sheet_num in [2, 3]:
            yplus = 396

        # Gallery, Piece ID and Barcode
        pdf.image(get_static_file_path('bidsheet.png'), x=xplus, y=yplus, w=306)
        pdf.set_font(normal_font_name, size=15)
        pdf.set_xy(154 + xplus, 27 + yplus)
        if self.gallery == c.GENERAL:
            pdf.cell(132, 22, txt="G", ln=1, align="L")
        else:
            pdf.cell(132, 22, txt="M", ln=1, align="L")
        pdf.set_font("3of9", size=27)
        pdf.set_xy(173 + xplus, 19 + yplus)
        pdf.cell(132, 22, txt=self.barcode_data, ln=1, align="C")
        pdf.set_font(bold_font_name, size=8)
        pdf.set_xy(173 + xplus, 38 + yplus)
        pdf.cell(132, 12, txt=self.artist_and_piece_id, ln=1, align="C")

        # Artist
        pdf.set_font(normal_font_name, size=12)
        set_fitted_font_size(self.app_display_name, max_size=260)
        pdf.set_xy(12 + xplus, 51 + yplus)
        pdf.cell(230, 24, txt=(self.app_display_name), ln=1, align="C")
        
        # Title
        set_fitted_font_size(self.name, max_size=260)
        pdf.set_xy(12 + xplus, 73 + yplus)
        pdf.cell(230, 24, txt=self.name, ln=1, align="C")
        
        # Media
        set_fitted_font_size(self.name, max_size=260)
        pdf.set_xy(12 + xplus, 94 + yplus)
        pdf.cell(230, 24, txt=self.media, ln=1, align="C")

        # Type: Print/Original
        # Display "Original", "Print", "Print X (Open Edition)", or "Print X of Y"
        
        if self.type == c.ORIGINAL:
            pdf.set_xy(232 + xplus, 50 + yplus)
            pdf.set_font(normal_font_name, size=12)
            pdf.cell(53, 24, txt="Original", ln=1, align="L")
        else: # PRINT
            # X of Y entered, display "Print X of Y"
            if self.print_run_num and self.print_run_total:
                pdf.set_font(normal_font_name, size=9)

                pdf.set_xy(233 + xplus, 45 + yplus)
                pdf.cell(53, 24, txt=f"Print", ln=1, align="L")

                pdf.set_xy(233 + xplus, 54 + yplus)
                pdf.cell(53, 24, txt=f"({self.print_run_num} of {self.print_run_total})", ln=1, align="L")
            # Only X entered, display "Print X (Open Edition)"
            elif self.print_run_num:
                pdf.set_font(normal_font_name, size=9)

                pdf.set_xy(233 + xplus, 45 + yplus)
                pdf.cell(53, 24, txt=f"Print {self.print_run_num}", ln=1, align="L")

                pdf.set_xy(233 + xplus, 54 + yplus)
                pdf.cell(53, 24, txt=f"Open Edition", ln=1, align="L")
            # No X of Y entered, display "Print"
            else:
                pdf.set_xy(241 + xplus, 50 + yplus)
                pdf.set_font(normal_font_name, size=12)
                pdf.cell(53, 24, txt="Print", ln=1, align="L")

        # Minimum Bid, QuickSale Price
        pdf.set_font(bold_font_name, size=11)
        pdf.set_xy(219 + xplus, 78 + yplus)
        pdf.cell(53, 14, txt=str(self.opening_bid) if self.valid_for_sale else 'NFS', ln=1, align="R")
        pdf.set_xy(219 + xplus, 99 + yplus)
        pdf.cell(53, 14, txt=str(self.quick_sale_price) if self.valid_quick_sale else 'NFS', ln=1, align="R")

    @property
    def artist_and_piece_id(self):
        if not self.app:
            return '???-' + str(self.piece_id)

        piece_id = self.piece_id
        if self.app.highest_piece_id > 99:
            piece_id = f"{piece_id:03}"
        else:
            piece_id = f"{piece_id:02}"

        if self.gallery == c.MATURE and self.app.artist_id_ad:
            return str(self.app.artist_id_ad) + "-" + piece_id
        return str(self.app.artist_id) + "-" + piece_id