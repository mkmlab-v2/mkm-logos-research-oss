import os
import smtplib
from email.message import EmailMessage


def main() -> int:
    host = os.environ["HOSTINGER_SMTP_HOST"]
    port = int(os.environ["HOSTINGER_SMTP_PORT"])
    user = os.environ["HOSTINGER_SMTP_USER"]
    password = os.environ["HOSTINGER_SMTP_PASS"]
    sender = os.environ.get("HOSTINGER_SMTP_SENDER", user)
    recipient = "admin@no1kmedi.com"

    message = EmailMessage()
    message["Subject"] = "[Smoke] Hostinger SMTP direct test"
    message["From"] = sender
    message["To"] = recipient
    message.set_content("Direct SMTP smoke from workspace automation.")

    use_ssl = str(os.environ.get("HOSTINGER_SMTP_SECURE", "true")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=20) as client:
            client.login(user, password)
            client.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=20) as client:
            client.starttls()
            client.login(user, password)
            client.send_message(message)

    print("smtp_direct_send: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
