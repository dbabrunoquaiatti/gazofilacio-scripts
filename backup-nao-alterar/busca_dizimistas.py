#!/usr/bin/env python3
import os
import json
import requests

API_URL = "https://hkcbddzaurlkopeypkgm.supabase.co/functions/v1/api-gateway/dizimistas"
TOKEN = os.getenv("SUPABASE_TOKEN")
OUTPUT_FILE = "/home/node/data/pessoas.json"

def fetch_dizimistas():
    if not TOKEN:
        print("ERROR: TOKEN not configured!")
        print("Set environment variable: export SUPABASE_TOKEN=your_token")
        return None

    try:
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        }

        dizimistas = []
        offset = 0
        limit = 100
        total_fetched = 0

        print("Fetching data with pagination...")

        while True:
            print(f"Fetching records from offset {offset} (limit {limit})...")

            params = {
                "limit": limit,
                "offset": offset
            }

            response = requests.get(API_URL, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()

            print(f"Response status: {response.status_code}")

            if "data" not in data:
                print("ERROR: 'data' field not found in response")
                break

            items = data["data"]
            print(f"Items in this batch: {len(items)}")

            if len(items) == 0:
                print("No more items to fetch")
                break

            for item in items:
                dizimistas.append({
                    "codigo_dizimista": item.get("codigo_dizimista"),
                    "nome_completo": item.get("nome_completo"),
                    "alias": item.get("alias")
                })
                total_fetched += 1

            if len(items) < limit:
                print("Got fewer items than limit - reached end")
                break

            offset += limit

        print(f"\nTotal records fetched: {total_fetched}")
        return dizimistas

    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def save_to_file(dados, filename):
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        print(f"Data saved to: {filename}")
        print(f"Total records: {len(dados)}")
        return True
    except Exception as e:
        print(f"File save error: {e}")
        return False

if __name__ == "__main__":
    dizimistas = fetch_dizimistas()

    if dizimistas:
        save_to_file(dizimistas, OUTPUT_FILE)
        print("\nFirst records:")
        for idx, dizimista in enumerate(dizimistas[:3], 1):
            print(f"  {idx}. {dizimista['nome_completo']} | Code: {dizimista['codigo_dizimista']} | Alias: {dizimista['alias']}")
    else:
        print("No data returned")