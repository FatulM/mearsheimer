import os

import requests
from dotenv import load_dotenv


def main():
    load_dotenv()
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        print("LLM_API_KEY not found in .env")
        return

    url = "https://api.avalai.ir/user/v1/credit"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    response = requests.get(url, headers=headers, timeout=30)

    data = response.json()

    print(f"Remaining (IRT): {data.get('remaining_irt', 'N/A'):,.2f}")
    print(f"Remaining ($):   {data.get('total_unit', 'N/A'):.16f}")
    print(f"Exchange rate:   {data.get('exchange_rate', 'N/A'):d}")
    print(f"Account Tier:    {data.get('account_tier', 'N/A'):d}")


if __name__ == "__main__":
    main()
