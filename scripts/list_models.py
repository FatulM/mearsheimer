#!/usr/bin/env python3
import json
import os
from decimal import Decimal

import requests
from dotenv import load_dotenv


def main():
    load_dotenv()
    base_url = os.getenv("LLM_BASE_URL", "").rstrip("/")
    api_key = os.getenv("LLM_API_KEY", "").strip()
    if not base_url or not api_key:
        print("LLM_BASE_URL and LLM_API_KEY must be set in .env")
        return

    url = f"{base_url}/models"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return

    print(f"Base URL: {base_url}")
    print()

    data = json.loads(response.text, parse_float=Decimal)

    # Dump data for debugging purposes:
    # print("Raw response data:")
    # print(json.dumps(data, indent=2, default=str))
    # print()

    models = data.get("data", [])
    if not models:
        print("No models found.")
        return

    show_pricing = "avalai" in base_url.lower()

    pricing_keys = [
        "cached_input",
        "input",
        "output",
        "input_above_128K",
        "output_above_128K",
        "input_above_200K",
        "output_above_200K",
    ]
    valid_pricing_keys = [k for k in pricing_keys if show_pricing]

    models.sort(key=lambda m: (m.get("owned_by", ""), m.get("id", "")))

    header_names = ["owner", "model"] + valid_pricing_keys
    rows = []
    for m in models:
        row = [m.get("owned_by", "-"), m.get("id", "-")]
        if show_pricing:
            pricing = m.get("pricing")
            if isinstance(pricing, dict):
                row.extend(str(pricing.get(key, "-")) for key in valid_pricing_keys)
            else:
                row.extend("-" for _ in valid_pricing_keys)
        rows.append(row)

    widths = [
        max(len(header_names[i]), *(len(r[i]) for r in rows))
        for i in range(len(header_names))
    ]

    print("  ".join(h.ljust(w) for h, w in zip(header_names, widths)))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print("  ".join(cell.ljust(w) for cell, w in zip(row, widths)))


if __name__ == "__main__":
    main()
