"""
EcoSight — Guardian / Emergency Contact Alert via Twilio SMS

When the phone-to-server connection is lost and cannot be re-established
after multiple retries, this module sends an SMS to the user's designated
guardian / emergency contact with the last known GPS location.

Flow:
    1. Client sends periodic heartbeats (ping) + GPS location updates.
    2. Server tracks last heartbeat timestamp per client.
    3. If a client disconnects and fails to reconnect after
       MAX_RECONNECT_ATTEMPTS (default 3) within the watchdog window,
       the server fires an SMS to the guardian with a Google Maps link
       showing the user's last known location.
"""

import os
from datetime import datetime, timezone

import config


def _get_twilio_client():
    """Lazy-import twilio so the rest of the server still works
    even if twilio is not installed (e.g. during development)."""
    try:
        from twilio.rest import Client
        account_sid = config.TWILIO_ACCOUNT_SID
        auth_token  = config.TWILIO_AUTH_TOKEN
        if not account_sid or not auth_token:
            print("[Guardian] Twilio credentials not configured — SMS disabled")
            return None
        return Client(account_sid, auth_token)
    except ImportError:
        print("[Guardian] twilio package not installed — SMS disabled")
        return None
    except Exception as e:
        print(f"[Guardian] Failed to initialise Twilio client: {e}")
        return None


def send_guardian_alert(
    *,
    latitude: float | None = None,
    longitude: float | None = None,
    user_name: str | None = None,
) -> bool:
    """
    Send an emergency SMS to the configured guardian number.

    Returns True if the SMS was queued successfully, False otherwise.
    """
    client = _get_twilio_client()
    if client is None:
        return False

    from_number = config.TWILIO_FROM_NUMBER
    to_number   = config.GUARDIAN_PHONE_NUMBER

    if not from_number or not to_number:
        print("[Guardian] Missing TWILIO_FROM_NUMBER or GUARDIAN_PHONE_NUMBER in config")
        return False

    # ── Build the message body ───────────────────────────────────
    name = user_name or config.USER_DISPLAY_NAME or "EcoSight User"
    now  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if latitude is not None and longitude is not None:
        maps_link = f"https://maps.google.com/?q={latitude},{longitude}"
        body = (
            f"⚠️ EcoSight Safety Alert\n\n"
            f"{name}'s device has lost connection to the EcoSight server "
            f"and could not reconnect after {config.WATCHDOG_MAX_RECONNECT_ATTEMPTS} attempts.\n\n"
            f"Last known location:\n{maps_link}\n\n"
            f"Time: {now}\n"
            f"Please check on them."
        )
    else:
        body = (
            f"⚠️ EcoSight Safety Alert\n\n"
            f"{name}'s device has lost connection to the EcoSight server "
            f"and could not reconnect after {config.WATCHDOG_MAX_RECONNECT_ATTEMPTS} attempts.\n\n"
            f"Last known location is unavailable.\n\n"
            f"Time: {now}\n"
            f"Please check on them."
        )

    # ── Send SMS ─────────────────────────────────────────────────
    try:
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=to_number,
        )
        print(f"[Guardian] ✓ SMS sent to {to_number}  (SID: {message.sid})")
        return True
    except Exception as e:
        print(f"[Guardian] ✗ SMS failed: {e}")
        return False
