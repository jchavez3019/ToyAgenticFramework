import os
from dotenv import dotenv_values

def summarize_value(value: str) -> str:
    """
    Returns the value with masked form ****last4 or the full string if the value
    is just a boolean value.
    :param value:
    :return:
    """
    lower = value.lower()
    if lower in ("true", "false"):
        return lower
    return "****" + value[-4:] if len(value) > 4 else "********"

def doublecheck_env(file_path: str):
    """Check environment variables against a .env file and print summaries."""
    if not os.path.exists(file_path):
        print(f"Did not find file {file_path}.")
        return

    parsed = dotenv_values(file_path)
    for key in parsed.keys():
        current = os.getenv(key)
        if current is not None:
            print(f"{key}={summarize_value(current)}")
        else:
            print(f"{key}=<not set>")