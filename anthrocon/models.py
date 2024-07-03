from pockets import classproperty
from residue import CoerceUTF8 as UnicodeText

from uber.config import c
from uber.models import Session
from uber.models.types import DefaultColumn as Column, MultiChoice
from uber.utils import get_static_file_path


@Session.model_mixin
class ArtShowApplication:
    agent_notes = Column(UnicodeText)


@Session.model_mixin
class ArtShowBidder:
    @classproperty
    def required_fields(cls):
        return {
            'badge_printed_name': "badge name or nickname",
            'first_name': "first name",
            'last_name': "last_name",
            'country': "country",
            'region': "region or city",
            'address1': "street address",
            'zip_code': "zip code or postal code",
            'cellphone': "phone number",
        }


@Session.model_mixin
class ArtShowPiece:
    def print_bidsheet(self, pdf, sheet_num, normal_font_name, bold_font_name, set_fitted_font_size):
        xplus = yplus = 0

        if sheet_num in [1, 3]:
            xplus = 305
        if sheet_num in [2, 3]:
            yplus = 394

        # Gallery, Piece ID and Barcode
        pdf.image(get_static_file_path('bidsheet.png'), x=0 + xplus, y=-2 + yplus, w=305)
        pdf.set_font(normal_font_name, size=17)
        if self.gallery == c.GENERAL:
            pdf.set_xy(153 + xplus, 9 + yplus)
        else:
            pdf.set_xy(153 + xplus, 20 + yplus)
        pdf.cell(132, 22, txt="O", ln=1, align="L")
        pdf.set_font("3of9", size=25)
        pdf.set_xy(178 + xplus, 8 + yplus)
        pdf.cell(132, 22, txt=self.barcode_data, ln=1, align="C")
        pdf.set_font(bold_font_name, size=8)
        pdf.set_xy(178 + xplus, 26 + yplus)
        pdf.cell(132, 12, txt=self.artist_and_piece_id, ln=1, align="C")

        # Artist, Title, Media
        pdf.set_font(normal_font_name, size=12)
        set_fitted_font_size(self.app_display_name, max_size=260)
        pdf.set_xy(10 + xplus, 41 + yplus)
        pdf.cell(230, 24,
                    txt=(self.app_display_name),
                    ln=1, align="C")
        pdf.set_xy(10 + xplus, 64 + yplus)
        set_fitted_font_size(self.name, max_size=260)
        pdf.cell(230, 24, txt=self.name, ln=1, align="C")
        pdf.set_font(normal_font_name, size=12)
        pdf.set_xy(10 + xplus, 86 + yplus)
        pdf.cell(
            230, 24,
            txt=f'Print ({self.print_run_num} of {self.print_run_total})' if self.type == c.PRINT else self.media,
            ln=1, align="C"
        )

        # Type, Minimum Bid, QuickSale Price
        pdf.set_font(bold_font_name, size=12)
        if self.type == c.PRINT:
            pdf.set_xy(235 + xplus, 43 + yplus)
        else:
            pdf.set_xy(235 + xplus, 33 + yplus)
        pdf.cell(53, 24, txt="x", ln=1, align="L")
        pdf.set_font(bold_font_name, size=12)
        pdf.set_xy(228 + xplus, 70 + yplus)
        pdf.cell(53, 14, txt=str(self.opening_bid) if self.valid_for_sale else 'NFS', ln=1, align="R")
        pdf.set_xy(228 + xplus, 92 + yplus)
        pdf.cell(
            53, 14, txt=str(self.quick_sale_price) if self.valid_quick_sale else 'NFS', ln=1, align="R")
        
    @property
    def barcode_data(self):
        return "".join(self.artist_and_piece_id.split("-"))
    
    @property
    def artist_and_piece_id(self):
        piece_id = self.piece_id
        if self.app.highest_piece_id > 99:
            piece_id = f"{piece_id:03}"
        else:
            piece_id = f"{piece_id:02}"

        if self.gallery == c.MATURE and self.app.artist_id_ad:
            return str(self.app.artist_id_ad) + "-" + piece_id
        return str(self.app.artist_id) + "-" + piece_id