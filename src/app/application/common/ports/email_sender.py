from typing import Protocol


class EmailSender(Protocol):
    """
    Port interface for sending emails.

    This protocol defines the contract for sending email messages
    from the application or domain layer without coupling to any
    specific delivery mechanism (e.g. SMTP, AWS SES, SendGrid).

    Implementations of this interface belong in the infrastructure
    layer and are responsible for the actual transmission of the email.

    Example use:
        email_sender.send(
            to="user@example.com",
            subject="Welcome!",
            body="Thanks for registering!"
        )

    Notes:
        - The application layer should depend on this protocol rather
          than on any concrete implementation.
        - Implementations should handle delivery failures gracefully
          and may choose to log or raise domain-specific exceptions.
    """

    def send(self, to: str, subject: str, body: str):
        """
        Sends an email message to the specified recipient.

        Args:
            to: The recipient's email address.
            subject: The subject line of the email.
            body: The plain text or HTML content of the email.

        Raises:
            EmailDeliveryError: If the email could not be delivered
                due to network, authentication, or provider issues.
        """
