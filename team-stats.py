import os
import json
import gspread
from google.oauth2.service_account import Credentials


SPREADSHEET_ID = "1hPnUsWFFjbFQZPrqc2F4X9f4ytjP2zb9sdhp8T0gjN0"


def get_google_sheet():

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly"
    ]

    credentials_info = json.loads(
        os.environ["GOOGLE_SERVICE_ACCOUNT"]
    )

    credentials = Credentials.from_service_account_info(
        credentials_info,
        scopes=scopes
    )

    client = gspread.authorize(credentials)

    return client.open_by_key(SPREADSHEET_ID)


def main():

    spreadsheet = get_google_sheet()

    iowa = spreadsheet.worksheet("Iowa")

    iowa_rows = iowa.get_all_values()

    print("========================================")
    print("IOWA TAB")
    print("========================================")

    for row_number, row in enumerate(iowa_rows, start=1):

        print(f"Row {row_number}: {row}")


if __name__ == "__main__":
    main()
