from dataclasses import dataclass

from app.application.common.exceptions.email import EmailDeliveryError
from app.application.common.ports.email_sender import EmailSender


class WordsToLearn:
    data: list[dict]


def convert_words_to_learn_to_str_email(words_to_learn: list[dict[str, str]]) -> str:
    """
    Convert a list of word dicts into an HTML email table string.

    Example input:
        [{"Italian": "fiore", "English": "flower"}, {"Italian": "cane", "English": "dog"}]

    Returns:
        str: HTML table with Language and English columns.
    """
    if not words_to_learn:
        return "<p>No words to learn today!</p>"

    # Get the foreign language key dynamically (the one that isn't 'English')
    sample = words_to_learn[0]
    foreign_lang = next((k for k in sample.keys() if k.lower() != "english"), "Foreign")

    # Build the HTML table
    html_rows = "".join(
        f"<tr><td>{entry.get(foreign_lang, '')}</td><td>{entry.get('English', '')}</td></tr>"
        for entry in words_to_learn
    )

    html_table = f"""
    <html>
        <body>
            <p>Here are your words to learn:</p>
            <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
                <tr>
                    <th>{foreign_lang}</th>
                    <th>English</th>
                </tr>
                {html_rows}
            </table>
            <p>Keep up the great work! 💪</p>
        </body>
    </html>
    """
    return html_table.strip()


@dataclass
class GameDigestEventMessage:
    username: str
    incorrect_words: list[dict]


class GameDigestInteractor:
    """
    :raises TypeError:
    :raises EmailDeliveryError:
    """

    def __init__(self, smtp_sender: EmailSender):
        self.smtp_sender = smtp_sender

    async def __call__(self, message: list[dict[str, str]]):
        try:
            game_digest_event_message = GameDigestEventMessage(**message)
        except TypeError:
            raise

        try:
            self.smtp_sender.send(
                game_digest_event_message.username,
                "Game completed! Make sure to learn these words!",
                convert_words_to_learn_to_str_email(game_digest_event_message.incorrect_words),
            )
        except EmailDeliveryError:
            raise
