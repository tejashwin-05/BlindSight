# EcoSight: Send Google Maps Link via Twilio SMS

from twilio.rest import Client
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, GUARDIAN_PHONE_NUMBER

# Twilio credentials (imported from config)
TWILIO_SID = TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN = TWILIO_AUTH_TOKEN
TWILIO_FROM = TWILIO_FROM_NUMBER

latitude = 17.537459740503298
longitude = 78.3854384918926

maps_url = f"https://maps.google.com/?q={latitude},{longitude}"
message_body = f"EcoSight Alert:\nUser location: {maps_url}"

client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

try:
    message = client.messages.create(
        body=message_body,
        from_=TWILIO_FROM,
        to=GUARDIAN_PHONE_NUMBER
    )
    print(f"SMS sent! SID: {message.sid}")
    print(f"Message: {message_body}")
except Exception as e:
    print(f"Failed to send SMS: {e}")
