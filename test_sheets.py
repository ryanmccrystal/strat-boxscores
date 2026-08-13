import os
import json
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1hPnUsWFFjbFQZPrqc2F4X9f4ytjP2zb9sdhp8T0gjN0"

scopes = [
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]

credentials_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT"])

credentials = Credentials.from_service_account_info(
    credentials_info,
    scopes=scopes
)

client = gspread.authorize(credentials)

spreadsheet = client.open_by_key(SPREADSHEET_ID)

standings = spreadsheet.worksheet("Standings")

rows = standings.get_all_values()

print(f"Found {len(rows)} rows in Standings.")

for row in rows[:10]:
    print(row)
