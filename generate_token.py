import jwt
import sys
from datetime import datetime, timedelta

# This secret key must be identical to the one in app/main.py
JWT_SECRET_KEY = "a-super-secret-key-that-is-long-and-secure"

def generate_token(email):
    """
    Generates a JWT for a given email address.

    Args:
        email (str): The email address to encode in the token.

    Returns:
        str: The generated JWT.
    """
    print(f"Generating token for email: {email}")
    payload = {
        'email': email,
        'exp': datetime.utcnow() + timedelta(days=30)  # Token expires in 30 days
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
    return token

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_token.py <email>")
        sys.exit(1)

    user_email = sys.argv[1]

    # Basic email format validation
    if '@' not in user_email or '.' not in user_email:
        print("Error: Please provide a valid email address.")
        sys.exit(1)

    generated_token = generate_token(user_email)

    print("\n--- Generated Token ---")
    print(generated_token)
    print("\nShare this token with the user. They can use it to log in.")
