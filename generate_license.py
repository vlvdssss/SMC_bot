#!/usr/bin/env python3
"""
License Key Generator for BAZA Trading Bot

Generates license keys for testing purposes.
"""

import hashlib
import datetime
import secrets

def generate_license_key(user_id: str = "demo", expiry_days: int = 30) -> str:
    """Generate a license key"""
    expiry = datetime.datetime.now() + datetime.timedelta(days=expiry_days)
    expiry_str = expiry.strftime("%Y%m%d")

    # Create unique key
    seed = f"{user_id}{expiry_str}{secrets.token_hex(8)}"
    key_hash = hashlib.sha256(seed.encode()).hexdigest()[:16].upper()

    return f"BAZA-{key_hash}-{expiry_str}"

if __name__ == "__main__":
    # Generate demo keys
    print("DEMO LICENSE KEYS:")
    for i in range(5):
        key = generate_license_key(f"demo{i}", 365)
        print(f"Key {i+1}: {key}")

    print("\nUse these keys for testing live mode.")