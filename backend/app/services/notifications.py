"""Notification abstraction. The MVP only logs a short, non-sensitive line.

TODO: plug in real providers (e.g. an email API, an SMS gateway for Nigerian numbers,
WhatsApp Business API) behind the same `notify()` call.
"""

import logging

log = logging.getLogger("propcheck.notifications")


def notify(user_id: int | None, event: str, summary: str) -> None:
    # Never include document contents, passwords or payment secrets in `summary`.
    log.info("notify user=%s event=%s %s", user_id, event, summary)
