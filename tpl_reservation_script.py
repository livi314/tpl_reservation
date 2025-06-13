
import os
from pathlib import Path

def load_credentials():
    # First try environment variables (used in GitHub Actions)
    library_card = os.getenv("TPL_LIBRARY_CARD")
    pin = os.getenv("TPL_PIN")
    if library_card and pin:
        return library_card, pin

    # Fallback to local .env file for local runs
    env_path = Path.home() / ".tpl_credentials.env"
    if not env_path.exists():
        print("First-time setup: Please enter your credentials")
        library_card = input("Enter your library card number: ")
        import getpass
        pin = getpass.getpass("Enter your PIN: ")
        with open(env_path, "w") as f:
            f.write(f"TPL_LIBRARY_CARD={library_card}\n")
            f.write(f"TPL_PIN={pin}\n")
        os.chmod(env_path, 0o600)
        print("Credentials stored securely!")
        return library_card, pin

    credentials = {}
    with open(env_path, "r") as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                credentials[key] = value

    return credentials.get("TPL_LIBRARY_CARD"), credentials.get("TPL_PIN")
