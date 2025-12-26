#!/usr/bin/env python3
"""
BAZA Paid License Generator
Generates paid licenses for BAZA Trading Bot with custom expiry dates.

Usage:
    python generate_paid_license.py --email user@example.com --months 12

This will create a license valid for 12 months from today.
"""

import argparse
import base64
import json
import hashlib
from datetime import datetime, timedelta
import os

def generate_license_key(email, expiry_date, license_type="paid"):
    """
    Generate a license key with email, expiry, and type.
    """
    data = {
        "email": email,
        "expiry": expiry_date.isoformat(),
        "type": license_type,
        "version": "1.0"
    }

    # Create a hash for verification
    data_str = json.dumps(data, sort_keys=True)
    hash_obj = hashlib.sha256(data_str.encode())
    data["hash"] = hash_obj.hexdigest()

    # Encode to base64
    json_str = json.dumps(data)
    encoded = base64.b64encode(json_str.encode()).decode()

    return f"BAZA-{encoded}"

def main():
    parser = argparse.ArgumentParser(description="Generate BAZA paid license")
    parser.add_argument("--email", required=True, help="Customer email")
    parser.add_argument("--months", type=int, default=12, help="License duration in months (default: 12)")
    parser.add_argument("--days", type=int, help="License duration in days (alternative to months)")

    args = parser.parse_args()

    # Calculate expiry date
    if args.days:
        expiry_date = datetime.now() + timedelta(days=args.days)
    else:
        expiry_date = datetime.now() + timedelta(days=args.months * 30)  # Approximate

    # Generate key
    license_key = generate_license_key(args.email, expiry_date)

    # Save to file
    output_file = f"license_{args.email.replace('@', '_').replace('.', '_')}.txt"
    with open(output_file, 'w') as f:
        f.write(f"BAZA Trading Bot License\n")
        f.write(f"Email: {args.email}\n")
        f.write(f"Expiry: {expiry_date.strftime('%Y-%m-%d')}\n")
        f.write(f"License Key: {license_key}\n")
        f.write(f"\nInstructions:\n")
        f.write(f"1. Download BAZA from https://github.com/vlvdssss/SMC_bot\n")
        f.write(f"2. Run main.py and enter this license key when prompted\n")
        f.write(f"3. For support: kamsaaaimpa@gmail.com\n")

    print(f"License generated for {args.email}")
    print(f"Expiry: {expiry_date.strftime('%Y-%m-%d')}")
    print(f"Key saved to: {output_file}")
    print(f"License Key: {license_key}")

if __name__ == "__main__":
    main()