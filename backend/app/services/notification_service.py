# Notification service for email and SMS
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from twilio.rest import Client
from flask import current_app

class NotificationService:
    def __init__(self):
        # Email configuration
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('FROM_EMAIL', 'noreply@smartfood.com')

        # SMS configuration (Twilio)
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')

        # Initialize Twilio client if credentials are available
        self.twilio_client = None
        if self.twilio_account_sid and self.twilio_auth_token:
            try:
                self.twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)
            except Exception as e:
                current_app.logger.warning(f"Failed to initialize Twilio client: {e}")

    def send_email(self, to_email, subject, body):
        """Send email notification"""
        try:
            if not self.smtp_username or not self.smtp_password:
                current_app.logger.warning("SMTP credentials not configured, skipping email")
                return False

            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'html'))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            text = msg.as_string()
            server.sendmail(self.from_email, to_email, text)
            server.quit()

            current_app.logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            current_app.logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_sms(self, to_phone, message):
        """Send SMS notification"""
        try:
            if not self.twilio_client:
                current_app.logger.warning("Twilio client not configured, skipping SMS")
                return False

            message = self.twilio_client.messages.create(
                body=message,
                from_=self.twilio_phone_number,
                to=to_phone
            )

            current_app.logger.info(f"SMS sent successfully to {to_phone}")
            return True

        except Exception as e:
            current_app.logger.error(f"Failed to send SMS to {to_phone}: {e}")
            return False

    def send_order_confirmation(self, user_email, user_phone, order_details):
        """Send order confirmation notifications"""
        order_id = order_details.get('id')
        restaurant_name = order_details.get('restaurant_name', 'SmartFood')
        total = order_details.get('total', 0)

        # Email content
        email_subject = f"Order Confirmed - #{order_id}"
        email_body = f"""
        <html>
        <body>
            <h2>Order Confirmation</h2>
            <p>Dear Customer,</p>
            <p>Your order has been confirmed!</p>
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>Order Details:</h3>
                <p><strong>Order ID:</strong> #{order_id}</p>
                <p><strong>Restaurant:</strong> {restaurant_name}</p>
                <p><strong>Total Amount:</strong> ${total:.2f}</p>
                <p><strong>Status:</strong> Confirmed</p>
            </div>
            <p>You will receive updates as your order progresses. Estimated delivery time: 30-45 minutes.</p>
            <p>Thank you for choosing SmartFood!</p>
            <br>
            <p>Best regards,<br>SmartFood Team</p>
        </body>
        </html>
        """

        # SMS content
        sms_message = f"SmartFood: Order #{order_id} confirmed! Total: ${total:.2f}. Estimated delivery: 30-45 mins. Track: app.smartfood.com/order/{order_id}"

        # Send notifications
        email_sent = self.send_email(user_email, email_subject, email_body)
        sms_sent = self.send_sms(user_phone, sms_message) if user_phone else False

        return {
            'email_sent': email_sent,
            'sms_sent': sms_sent
        }

    def send_order_status_update(self, user_email, user_phone, order_details, new_status):
        """Send order status update notifications"""
        order_id = order_details.get('id')
        status_messages = {
            'preparing': 'is being prepared',
            'ready': 'is ready for pickup',
            'out_for_delivery': 'is out for delivery',
            'delivered': 'has been delivered'
        }

        status_message = status_messages.get(new_status, 'status has been updated')

        # Email content
        email_subject = f"Order Update - #{order_id}"
        email_body = f"""
        <html>
        <body>
            <h2>Order Status Update</h2>
            <p>Dear Customer,</p>
            <p>Your order #{order_id} {status_message}.</p>
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Order ID:</strong> #{order_id}</p>
                <p><strong>New Status:</strong> {new_status.replace('_', ' ').title()}</p>
            </div>
            {"<p>You can track your order in real-time through our app.</p>" if new_status != 'delivered' else "<p>We hope you enjoyed your meal! Please rate your experience.</p>"}
            <p>Thank you for choosing SmartFood!</p>
            <br>
            <p>Best regards,<br>SmartFood Team</p>
        </body>
        </html>
        """

        # SMS content
        sms_message = f"SmartFood: Order #{order_id} {status_message}. {'Track: app.smartfood.com/order/' + str(order_id) if new_status != 'delivered' else 'Enjoy your meal!'}"

        # Send notifications
        email_sent = self.send_email(user_email, email_subject, email_body)
        sms_sent = self.send_sms(user_phone, sms_message) if user_phone else False

        return {
            'email_sent': email_sent,
            'sms_sent': sms_sent
        }