import resend
from config import settings, logger

resend.api_key = settings.RESEND_API_KEY


def send_email(to: str, subject: str, html: str) -> bool:
    """Reusable email sender for the whole platform (auth, notifications,
    future modules). Never raises — logs and returns False on failure so
    callers can decide how to handle it without crashing the request."""
    try:
        resend.Emails.send({
            "from": settings.RESEND_FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        return True
    except Exception as e:
        logger.error(f"Resend send failed to {to}: {e}")
        return False


def send_otp_email(to: str, otp: str, purpose: str) -> bool:
    if purpose == "signup":
        subject = "Verify your Workforge account"
        heading = "Verify your email"
        body = "Enter this code to finish creating your Workforge account."
    else:
        subject = "Reset your Workforge password"
        heading = "Reset your password"
        body = "Enter this code to reset your password."

    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
      <h2>{heading}</h2>
      <p>{body}</p>
      <p style="font-size: 32px; font-weight: 700; letter-spacing: 6px; margin: 24px 0;">{otp}</p>
      <p style="color: #666; font-size: 13px;">This code expires in {settings.OTP_EXPIRY_MINUTES} minutes. If you didn't request this, you can ignore this email.</p>
    </div>
    """
    return send_email(to, subject, html)
