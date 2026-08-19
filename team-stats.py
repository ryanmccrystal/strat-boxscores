import os
import json
import html
import gspread
from google.oauth2.service_account import Credentials


SPREADSHEET_ID = "1hPnUsWFFjbFQZPrqc2F4X9f4ytjP2zb9sdhp8T0gjN0"

TEAM_TAB = "Iowa"


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


def html_escape(value):

    return html.escape(
        str(value),
        quote=True
    )


def get_iowa_data(spreadsheet):

    worksheet = spreadsheet.worksheet(
        TEAM_TAB
    )

    return worksheet.get_all_values()


def find_section_rows(rows):

    sections = {}

    for index, row in enumerate(rows):

        values = [
            cell.strip()
            for cell in row
        ]

        if "Pitching" in values:
            sections["Pitching"] = index

        elif "Batting" in values:
            sections["Batting"] = index

        elif "Catching" in values:
            sections["Catching"] = index

        elif "Fielding" in values:
            sections["Fielding"] = index

    return sections


def get_section_rows(
    rows,
    section_start,
    next_section_start=None
):

    start = section_start + 1

    if next_section_start is not None:
        end = next_section_start
    else:
        end = len(rows)

    section = rows[start:end]

    # Remove completely blank rows at the beginning/end.
    while section and not any(
        cell.strip()
        for cell in section[0]
    ):
        section.pop(0)

    while section and not any(
        cell.strip()
        for cell in section[-1]
    ):
        section.pop()

    return section


def make_table(
    section_rows,
    section_name
):

    if len(section_rows) < 2:
        return ""

    header = section_rows[0]

    data_rows = section_rows[1:]

    # Find the actual used columns.
    last_column = 0

    for row in section_rows:

        for index, value in enumerate(row):

            if value.strip():
                last_column = max(
                    last_column,
                    index
                )

    header = header[:last_column + 1]

    html_output = """
    <div class="table-wrapper">
        <table class="team-stats-table">
            <thead>
                <tr>
    """

    for value in header:

        html_output += (
            f"<th>{html_escape(value)}</th>"
        )

    html_output += """
                </tr>
            </thead>
            <tbody>
    """

    for row_index, row in enumerate(data_rows):

        row = row[:last_column + 1]
    
        # Divider after the fourth starting pitcher.
        if (
            section_name == "Pitching"
            and row_index == 4
        ):
            html_output += """
                    <tr class="section-divider">
                        <td colspan="100%"></td>
                    </tr>
            """
    
        # Divider immediately before the Team row.
        if (
            section_name == "Pitching"
            and row
            and row[0].strip() == "Team"
        ):
            html_output += """
                    <tr class="section-divider">
                        <td colspan="100%"></td>
                    </tr>
            """
    
        html_output += "<tr>"
    
        for value in row:
    
            html_output += (
                f"<td>{html_escape(value)}</td>"
            )
    
        # Fill any missing cells.
        missing = len(header) - len(row)
    
        for _ in range(missing):
    
            html_output += "<td></td>"
    
        html_output += "</tr>"

    html_output += """
            </tbody>
        </table>
    </div>
    """

    return html_output


def make_team_page(rows):

    sections = find_section_rows(
        rows
    )

    html_output = """
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>Iowa Cubs - Strat-o-Matic</title>

<link rel="preconnect"
      href="https://fonts.googleapis.com">

<link rel="preconnect"
      href="https://fonts.gstatic.com" crossorigin>

<link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&display=swap"
      rel="stylesheet">

<style>

    body {
        font-family:
            "Source Sans 3",
            Arial,
            Helvetica,
            sans-serif;

        background: #ffffff;
        color: #111111;

        margin: 0;
        padding: 25px;
    }

    .container {
        width: 100%;
        margin: 0 auto;
    }

    .team-header {
        margin-bottom: 25px;
    }

    .team-name {
        font-size: 32px;
        font-weight: 700;
        margin: 0 0 3px 0;
    }

    .team-record {
        font-size: 18px;
        margin-bottom: 2px;
    }

    .team-manager {
        font-size: 16px;
        color: #555555;
    }

    .stats-section {
        margin-bottom: 28px;
    }

    .stats-section h2 {
        font-size: 20px;
        font-weight: 700;
        margin: 0 0 6px 0;
        border-bottom: 1px solid #222;
        padding-bottom: 3px;
    }

    .table-wrapper {
        width: 100%;
        overflow-x: auto;
    }

    .team-stats-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: auto;
        font-size: 14px;
        white-space: nowrap;
    }

    .team-stats-table th,
    .team-stats-table td {
        padding: 4px 7px;
        text-align: center;
        line-height: 1.15;
    }

    .team-stats-table tr.section-divider {
        height: 0;
    }
    
    .team-stats-table tr.section-divider td {
        padding: 0;
        height: 0;
        line-height: 0;
        border-bottom: 1px solid #222;
    }

    .team-stats-table th:nth-child(1),
    .team-stats-table td:nth-child(1),
    .team-stats-table th:nth-child(2),
    .team-stats-table td:nth-child(2) {
        text-align: left;
    }

    .team-stats-table th {
        font-weight: 600;
        border-bottom: 1px solid #222;
    }

    .team-stats-table tbody tr:last-child {
        border-bottom: 1px solid #222;
    }

    .team-stats-table tbody tr:hover {
        background: #f5f5f5;
    }

    .team-stats-table tr.section-divider {
        border-bottom: 1px solid #222;
    }

    @media (max-width: 900px) {

        body {
            padding: 15px;
        }

        .team-name {
            font-size: 28px;
        }

        .team-stats-table {
            font-size: 13px;
        }

        .team-stats-table th,
        .team-stats-table td {
            padding: 3px 5px;
        }
    }

</style>

</head>

<body>

<div class="container">
"""

    # Team header
    team_name = ""

    if rows and len(rows[0]) > 2:
        team_name = rows[0][2].strip()

    record = ""

    if len(rows) > 1 and len(rows[1]) > 2:
        record = rows[1][2].strip()

    manager = ""

    if len(rows) > 1 and len(rows[1]) > 3:
        manager = rows[1][3].strip()

    html_output += f"""
    <div class="team-header">

        <div class="team-name">
            {html_escape(team_name)}
        </div>

        <div class="team-record">
            {html_escape(record)}
        </div>

        <div class="team-manager">
            {html_escape(manager)}
        </div>

    </div>
    """

    # Sort sections according to their appearance
    # in the spreadsheet.
    ordered_sections = sorted(
        sections.items(),
        key=lambda item: item[1]
    )

    for section_index, (
        section_name,
        start
    ) in enumerate(ordered_sections):

        if section_index + 1 < len(
            ordered_sections
        ):

            next_start = ordered_sections[
                section_index + 1
            ][1]

        else:

            next_start = None

        section_rows = get_section_rows(
            rows,
            start,
            next_start
        )

        html_output += f"""
    <section class="stats-section">

        <h2>
            {html_escape(section_name)}
        </h2>
    """

        html_output += make_table(
            section_rows,
            section_name
        )

        html_output += """
    </section>
    """

    html_output += """
</div>

</body>
</html>
"""

    return html_output


def main():

    spreadsheet = get_google_sheet()

    rows = get_iowa_data(
        spreadsheet
    )

    html_output = make_team_page(
        rows
    )

    os.makedirs(
        "teams",
        exist_ok=True
    )

    with open(
        "teams/iowa.html",
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            html_output
        )

    print(
        "Created teams/iowa.html"
    )


if __name__ == "__main__":
    main()
