"""
Email utilities for sending receipt emails with PDF attachments
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from datetime import datetime


class NumberedCanvas(canvas.Canvas):
    """Custom canvas for adding page numbers and headers/footers"""
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count):
        # Page size
        page_width, page_height = A4
        
        # Header decoration - Gold gradient bar
        self.setFillColorRGB(1, 0.77, 0.07)  # Gold color
        self.rect(0, page_height - 0.5*cm, page_width, 0.5*cm, fill=1, stroke=0)
        
        # Footer decoration
        self.setFillColorRGB(1, 0.77, 0.07)
        self.rect(0, 0, page_width, 0.5*cm, fill=1, stroke=0)
        
        # Page number
        self.setFont('Helvetica', 9)
        self.setFillColorRGB(0.4, 0.4, 0.4)
        page_num_text = f"Page {self._pageNumber} of {page_count}"
        self.drawCentredString(page_width / 2, 1*cm, page_num_text)
        
        # Footer text
        self.setFont('Helvetica-Oblique', 8)
        self.drawCentredString(page_width / 2, 1.5*cm, "Dwarka Yatra - Registration Receipt")


def generate_receipt_pdf(passengers, total_amount):
    """
    Generate an attractive A4 PDF receipt for the Yatra booking
    One page per traveler with comprehensive details
    
    Args:
        passengers: List of Passenger objects
        total_amount: Total payment amount
        
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        topMargin=1.5*cm,
        bottomMargin=2.5*cm,
        leftMargin=2*cm,
        rightMargin=2*cm
    )
    elements = []
    
    # Define custom styles
    styles = getSampleStyleSheet()
    
    # Title style - Large and bold
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor('#ffc107'),
        spaceAfter=5,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        leading=34
    )
    
    # Subtitle style
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#666666'),
        spaceAfter=15,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique'
    )
    
    # Section heading style
    section_heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#ffc107'),
        spaceAfter=10,
        spaceBefore=12,
        fontName='Helvetica-Bold',
        backColor=colors.HexColor('#FFF8E1')
    )
    
    # Traveler name style
    traveler_name_style = ParagraphStyle(
        'TravelerName',
        parent=styles['Heading3'],
        fontSize=18,
        textColor=colors.HexColor('#ff9800'),
        spaceAfter=8,
        spaceBefore=5,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER
    )
    
    normal_style = styles['Normal']
    
    # ==================== ONE PAGE PER TRAVELER ====================
    
    for idx, passenger in enumerate(passengers, 1):
        # Header - Title
        title = Paragraph("DWARKA YATRA", title_style)
        elements.append(title)
        
        subtitle = Paragraph("Registration Receipt", subtitle_style)
        elements.append(subtitle)
        
        # Decorative line
        line_table = Table([['']], colWidths=[17*cm])
        line_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 3, colors.HexColor('#ffc107')),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#ff9800')),
        ]))
        elements.append(line_table)
        elements.append(Spacer(1, 0.4*cm))
        
        # Success badge
        success_box = Table([
            [Paragraph("<b>✓ PAYMENT SUCCESSFUL</b>", 
                       ParagraphStyle('Success', parent=normal_style, fontSize=16, 
                                    textColor=colors.white, alignment=TA_CENTER))]
        ], colWidths=[17*cm])
        success_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#28a745')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        elements.append(success_box)
        elements.append(Spacer(1, 0.5*cm))
        
        # Traveler indicator
        traveler_indicator = Paragraph(
            f"<b>Traveler {idx} of {len(passengers)}</b>",
            ParagraphStyle('Indicator', parent=normal_style, fontSize=11, 
                         textColor=colors.HexColor('#666666'), alignment=TA_CENTER)
        )
        elements.append(traveler_indicator)
        elements.append(Spacer(1, 0.2*cm))
        
        # Traveler name in large text
        traveler_name = Paragraph(f"<b>{passenger.name}</b>", traveler_name_style)
        elements.append(traveler_name)
        elements.append(Spacer(1, 0.4*cm))
        
        # Personal Information Section
        personal_heading = Paragraph("📋 Personal Information", section_heading_style)
        elements.append(personal_heading)
        
        personal_data = [
            ['Full Name:', passenger.name],
            ['Age:', f'{passenger.age} years'],
            ['Gender:', passenger.gender],
        ]
        
        if passenger.email:
            personal_data.append(['Email:', passenger.email])
        if passenger.phone:
            personal_data.append(['Phone:', passenger.phone])
        if passenger.alternative_phone:
            personal_data.append(['Alternative Phone:', passenger.alternative_phone])
        if passenger.city:
            personal_data.append(['City:', passenger.city])
        if passenger.district:
            personal_data.append(['District:', passenger.district])
        if passenger.state:
            personal_data.append(['State:', passenger.state])
        
        personal_table = Table(personal_data, colWidths=[6*cm, 11*cm])
        personal_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E3F2FD')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#BBDEFB')),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ]))
        elements.append(personal_table)
        elements.append(Spacer(1, 0.4*cm))
        
        # Package Details Section
        package_heading = Paragraph("📦 Package Details", section_heading_style)
        elements.append(package_heading)
        
        package_data = [
            ['Package Type:', passenger.yatra_class],
        ]
        
        # Add journey details if available
        if hasattr(passenger, 'journey_start_date') and passenger.journey_start_date:
            package_data.append(['Journey Start:', passenger.journey_start_date.strftime('%d %B %Y')])
        if hasattr(passenger, 'journey_end_date') and passenger.journey_end_date:
            package_data.append(['Journey End:', passenger.journey_end_date.strftime('%d %B %Y')])
        if hasattr(passenger, 'num_days') and passenger.num_days:
            package_data.append(['Duration:', f'{passenger.num_days} days'])
        if hasattr(passenger, 'hotel_category') and passenger.hotel_category:
            package_data.append(['Hotel Category:', passenger.hotel_category.capitalize()])
        if hasattr(passenger, 'travel_medium') and passenger.travel_medium:
            travel_text = passenger.travel_medium.capitalize()
            if passenger.travel_medium in ['train', 'flight']:
                travel_text += ' (Delhi to Dwarka)'
            package_data.append(['Travel Medium:', travel_text])
        if hasattr(passenger, 'has_otm') and passenger.has_otm and hasattr(passenger, 'otm_id') and passenger.otm_id:
            package_data.append(['OTM Status:', f'Verified ✓ (ID: {passenger.otm_id})'])
        
        package_table = Table(package_data, colWidths=[6*cm, 11*cm])
        package_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#FFF3E0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#FFE0B2')),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ]))
        elements.append(package_table)
        elements.append(Spacer(1, 0.4*cm))
        
        # Payment Information Section
        payment_info_heading = Paragraph("💳 Payment Information", section_heading_style)
        elements.append(payment_info_heading)
        
        payment_info_data = [
            ['Amount Paid:', f'₹ {passenger.amount:,.2f}'],
            ['Payment Status:', 'PAID ✓'],
            ['Payment Date:', passenger.created_at.strftime('%d %B %Y, %I:%M %p')],
            ['Order ID:', passenger.razorpay_order_id],
        ]
        
        if passenger.razorpay_payment_id:
            payment_info_data.append(['Payment ID:', passenger.razorpay_payment_id])
        
        payment_info_table = Table(payment_info_data, colWidths=[6*cm, 11*cm])
        payment_info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F5E9')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#C8E6C9')),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ]))
        elements.append(payment_info_table)
        elements.append(Spacer(1, 0.4*cm))

        # Important Note about Travel Cost
        note_style = ParagraphStyle(
            'NoteStyle',
            parent=normal_style,
            fontSize=9,
            textColor=colors.HexColor('#D32F2F'), # Red color for attention
            alignment=TA_LEFT,
            borderColor=colors.HexColor('#ffcc80'),
            borderWidth=1,
            borderPadding=10,
            backColor=colors.HexColor('#fff3e0')
        )
        
        note = Paragraph(
            "<b>IMPORTANT NOTE:</b> We have NOT charged for your traveling cost. " 
            "Traveling cost depends entirely on whether you choose to travel by train or flight.", 
            note_style
        )
        elements.append(note)
        
        # Add page break between travelers (except for the last one)
        if idx < len(passengers):
            elements.append(PageBreak())
    
    # Build PDF with custom canvas
    doc.build(elements, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer


def send_receipt_email(to_email, pdf_buffer, passengers, total_amount, gmail_address, gmail_app_password):
    """
    Send receipt email with PDF attachment via Gmail SMTP
    
    Args:
        to_email: Recipient email address
        pdf_buffer: BytesIO buffer containing the PDF
        passengers: List of Passenger objects
        total_amount: Total payment amount
        gmail_address: Gmail sender address
        gmail_app_password: Gmail app password
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = gmail_address
        msg['To'] = to_email
        msg['Subject'] = 'Dwarka Yatra - Your Registration Confirmed! 🙏'
        
        # Create HTML email body
        traveler_names = ', '.join([p.name for p in passengers])
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                        <h1 style="color: white; margin: 0; font-size: 28px;">🦚 Dwarka Yatra</h1>
                        <p style="color: white; margin: 10px 0 0 0; font-size: 16px;">Registration Confirmed</p>
                    </div>
                    
                    <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                        <h2 style="color: #ffc107; margin-top: 0;">Hare Krishna! 🙏</h2>
                        
                        <p>Thank you for registering for Dwarka Yatra. Your booking has been confirmed and payment has been received successfully.</p>
                        
                        <div style="background: white; padding: 20px; border-left: 4px solid #ffc107; margin: 20px 0;">
                            <h3 style="margin-top: 0; color: #ff9800;">Booking Summary</h3>
                            <p style="margin: 5px 0;"><strong>Traveler(s):</strong> {traveler_names}</p>
                            <p style="margin: 5px 0;"><strong>Total Travelers:</strong> {len(passengers)}</p>
                            <p style="margin: 5px 0;"><strong>Total Amount:</strong> ₹{total_amount:,.2f}</p>
                            <p style="margin: 5px 0;"><strong>Payment Status:</strong> <span style="color: #28a745; font-weight: bold;">PAID ✓</span></p>
                        </div>
                        
                        <p>Your detailed receipt is attached to this email as a PDF document. Please keep it for your records.</p>
                        
                        <div style="background: white; padding: 20px; border-left: 4px solid #25D366; margin: 20px 0; text-align: center;">
                            <h3 style="margin-top: 0; color: #25D366;">📱 Join Our WhatsApp Group</h3>
                            <p style="margin: 10px 0;">Stay connected with us and other travelers! Join our official WhatsApp group for updates, information, and community support.</p>
                            <a href="https://chat.whatsapp.com/IKqLI5yzpI21DGCZ6Q0v4N" style="display: inline-block; background: #25D366; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 10px;">Join WhatsApp Group</a>
                        </div>
                        
                        <p style="margin-top: 30px;">If you have any questions or need assistance, please don't hesitate to contact us.</p>
                        
                        <p style="margin-top: 20px;">
                            <strong>Hari Hari!</strong><br>
                            Team Dwarka Yatra
                        </p>
                    </div>
                    
                    <div style="text-align: center; margin-top: 20px; padding: 20px; color: #666; font-size: 12px;">
                        <p>This is an automated email. Please do not reply to this message.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Attach HTML body
        msg.attach(MIMEText(html_body, 'html'))
        
        # Attach PDF
        pdf_attachment = MIMEApplication(pdf_buffer.read(), _subtype='pdf')
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename='Dwarka_Yatra_Receipt.pdf')
        msg.attach(pdf_attachment)
        
        # Send email via Gmail SMTP
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(gmail_address, gmail_app_password)
            server.send_message(msg)
            
        print(f"[SUCCESS] ✅ Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        print(f"[ERROR] ❌ Failed to send email: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
