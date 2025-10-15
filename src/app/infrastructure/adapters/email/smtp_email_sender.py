import base64
from email.message import EmailMessage

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.application.common.exceptions.email import EmailDeliveryError
from app.application.common.ports.email_sender import EmailSender
from app.config import Config


class SmtpEmailSender(EmailSender):
    def __init__(self, config: Config):
        self.config = config

    async def send(self, to: str, subject: str, body: str):
        try:
            self.gmail_send_message(to, subject, body)
        except HttpError:
            raise EmailDeliveryError

    def gmail_send_message(self, to: str, subject: str, body: str):
        """Create and send an email message
        Print the returned  message id
        Returns: Message object, including message id

        Load pre-authorized user credentials from the environment.
        TODO(developer) - See https://developers.google.com/identity
        for guides on implementing OAuth2 for the application.
        """
        try:
            creds = Credentials.from_authorized_user_file("token.json")

            service = build("gmail", "v1", credentials=creds)
            message = EmailMessage()

            message.add_alternative(body, subtype="html")

            message["To"] = to
            message["From"] = self.config.EMAIL_USERNAME
            message["Subject"] = subject

            # encoded message
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            create_message = {"raw": encoded_message}
            # pylint: disable=E1101
            send_message = service.users().messages().send(userId="me", body=create_message).execute()
            print(f"Message Id: {send_message['id']}")
        except HttpError as error:
            print(f"An error occurred: {error}")
            send_message = None
        return send_message
