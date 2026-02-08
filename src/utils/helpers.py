import random
import string
from datetime import datetime, timedelta


def generate_verification_code(length: int = 4) -> str:
    """Generate a numeric verification code of given length."""
    return "".join(random.choices(string.digits, k=length))


def get_code_expiration(minutes: int = 10) -> datetime:
    """Get the expiration time for a verification code."""
    return datetime.now() + timedelta(minutes=minutes)


def send_email_mock(email: str, code: str) -> None:
    """Mock function to simulate sending an email with the verification code."""
    print(f"Sending verification code {code} to email: {email}")
