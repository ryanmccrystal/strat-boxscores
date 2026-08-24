import os
import re
import json
import html

import gspread
from google.oauth2.service_account import Credentials


# ============================================================
# SETTINGS
# ============================================================

# Use the same spreadsheet ID as team-stats.py.
SPREADSHEET_ID = "YOUR_SPREADSHEET_ID"


# Use the same team tab list as team-stats.py.
TEAM_TABS = [
    "Iowa",
    "Omaha",
    "Richmond",
    # Add the rest of your team tabs here.
]


OUTPUT_FILE = "batting-stats.html"


# ============================================================
# GOOGLE SHEETS
# ============================================================

def get_google_sheet():

    service_account_info = json.loads(
        os.environ["GOOGLE_SERVICE_ACCOUNT"]
    )

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly"
    ]

    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=scopes
    )

    client = gspread.authorize(
        credentials
    )

    spreadsheet = client.open_by_key(
        SPREADSHEET_ID
    )

    return spreadsheet


# ============================================================
# HTML
# ============================================================

def html_escape(value):

    return html.escape(
        str(value)
    )


# ============================================================
# FIND BATTING SECTION
# ============================================================

def find_batting_section(rows):

    batting_start = None

    for index, row in enumerate(rows):

        for value in row:

            if value.strip() == "Batting":

                batting_start = index

                break

        if batting_start is not None:

            break


    if batting_start is None:

        return []


    # Find the next section after Batting.
    section_names = [
        "Pitching",
        "Catching",
        "Fielding"
    ]

    batting_end = len(rows)


    for index in range(
        batting_start + 1,
        len(rows)
    ):

        row = rows[index]

        found_section = False

        for value in row:

            if value.strip() in section_names:

                batting_end = index

                found_section = True

                break

        if found_section:

            break


    return rows[
        batting_start:batting_end
    ]


# ============================================================
# GET BATTING DATA FOR ONE TEAM
# ============================================================

def get_team_batting_data(
    spreadsheet,
    team_tab
):

    worksheet = spreadsheet.worksheet(
        team_tab
    )

    rows = worksheet.get_all_values()

    batting_rows = find_batting_section(
        rows
    )

    if not batting_rows:

        print(
            f"WARNING: No Batting section found for {team_tab}"
        )

        return []


    # The first row is the "Batting" section
    # heading. The actual table follows it.
    data_rows = batting_rows[1:]


    # Remove completely empty rows.
    data_rows = [
        row
        for row in data_rows
        if any(
            value.strip()
            for value in row
        )
    ]


    return data_rows


# ============================================================
# DETERMINE TABLE HEADER
# ============================================================

def find_header_row(rows):

    for index, row in enumerate(rows):

        # Look for the normal batting headers.
        if (
            "Player" in row
            or "Name" in row
        ):

            return index


    return 0


# ============================================================
# BUILD ALL BATTING DATA
# ============================================================

def get_all_batting_data(
    spreadsheet
):

    all_teams = []

    for team_tab in TEAM_TABS:

        print(
            f"Reading batting stats: {team_tab}"
        )

        rows = get_team_batting_data(
            spreadsheet,
            team_tab
        )

        if not rows:

            continue


        header_index = find_header_row(
            rows
        )

        headers = rows[
            header_index
        ]

        player_rows = rows[
            header_index + 1:
        ]


        for row in player_rows:

            # Ignore empty rows.
            if not any(
                value.strip()
                for value in row
            ):

                continue


            # Ignore the Team Totals row.
            if any(
                value.strip() == "Team"
                for value in row
            ):

                continue


            # Ignore rows that don't appear to
            # contain a player name.
            player_name = ""

            if len(row) > 0:

                player_name = row[0].strip()


            if not player_name:

                continue


            all_teams.append(
                {
                    "team": team_tab,
                    "headers": headers,
                    "values": row
                }
            )


    return all_teams


# ============================================================
# TABLE
# ============================================================

def make_batting_table(
    batting_data
):

    if not batting_data:

        return """
        <p>No batting data found.</p>
        """


    headers = batting_data[0]["headers"]


    html_output = """
    <table
        id="batting-table"
        class="stats-table"
    >

        <thead>

            <tr>

                <th
                    class="team-column sortable"
                    data-column="team"
                >
                    Team
                </th>
    """


    for column_index, header in enumerate(
        headers
    ):

        if not header.strip():

            continue


        html_output += f"""
                <th
                    class="sortable"
                    data-column="{column_index}"
                >
                    {html_escape(header)}
                </th>
        """


    html_output += """
            </tr>

        </thead>

        <tbody>
    """


    for player in batting_data:

        team = player["team"]

        values = player["values"]


        html_output += """
            <tr>
        """


        html_output += f"""
                <td class="team-column">
                    {html_escape(team)}
                </td>
        """


        for value in values:

            html_output += f"""
                <td>
                    {html_escape(value)}
                </td>
            """


        html_output += """
            </tr>
        """


    html_output += """
        </tbody>

    </table>
    """


    return html_output


# ============================================================
# PAGE
# ============================================================

def make_page(
    batting_data
):

    html_output = """
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>Batting Stats - Strat-o-Matic</title>

<link
    rel="preconnect"
    href="https://fonts.googleapis.com"
>

<link
    rel="preconnect"
    href="https://fonts.gstatic.com"
    crossorigin
>

<link
    href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&display=swap"
    rel="stylesheet"
>

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


    h1 {

        font-size: 32px;

        margin: 0 0 20px 0;
    }


    .stats-table {

        width: 100%;

        border-collapse: collapse;

        table-layout: auto;
    }


    .stats-table th,
    .stats-table td {

        padding: 5px 7px;

        border-bottom: 1px solid #dddddd;

        white-space: nowrap;

        text-align: center;

        font-size: 14px;
    }


    .stats-table th {

        font-weight: 700;

        background: #f2f2f2;

        cursor: pointer;

        user-select: none;
    }


    .stats-table th:hover {

        background: #e5e5e5;
    }


    .stats-table td.team-column,
    .stats-table th.team-column {

        text-align: left;

        font-weight: 600;
    }


    .stats-table tbody tr:hover {

        background: #f5f5f5;
    }


    .sortable::after {

        content: " ↕";

        font-size: 11px;

        color: #888888;
    }


    .sortable.sort-ascending::after {

        content: " ▲";

        color: #111111;
    }


    .sortable.sort-descending::after {

        content: " ▼";

        color: #111111;
    }


    @media (max-width: 900px) {

        body {

            padding: 15px;
        }


        .stats-table th,
        .stats-table td {

            padding: 4px 5px;

            font-size: 13px;
        }
    }

</style>

</head>

<body>

<div class="container">

    <h1>
        Batting Stats
    </h1>
"""


    html_output += make_batting_table(
        batting_data
    )


    html_output += """

</div>


<script>

document.addEventListener(
    "DOMContentLoaded",
    function() {

        const table =
            document.getElementById(
                "batting-table"
            );

        if (!table) {

            return;
        }


        const headers =
            table.querySelectorAll(
                "thead th.sortable"
            );


        headers.forEach(
            function(header) {

                header.addEventListener(
                    "click",
                    function() {

                        const column =
                            header.dataset.column;

                        const tbody =
                            table.querySelector(
                                "tbody"
                            );

                        const rows =
                            Array.from(
                                tbody.querySelectorAll(
                                    "tr"
                                )
                            );


                        const currentDirection =
                            header.classList.contains(
                                "sort-ascending"
                            )
                                ? "descending"
                                : "ascending";


                        headers.forEach(
                            function(otherHeader) {

                                otherHeader.classList.remove(
                                    "sort-ascending"
                                );

                                otherHeader.classList.remove(
                                    "sort-descending"
                                );
                            }
                        );


                        header.classList.add(
                            "sort-" +
                            currentDirection
                        );


                        rows.sort(
                            function(a, b) {

                                let aValue;
                                let bValue;


                                if (
                                    column ===
                                    "team"
                                ) {

                                    aValue =
                                        a.children[0]
                                            .textContent
                                            .trim();

                                    bValue =
                                        b.children[0]
                                            .textContent
                                            .trim();

                                } else {

                                    const index =
                                        parseInt(
                                            column
                                        ) + 1;

                                    aValue =
                                        a.children[index]
                                            .textContent
                                            .trim();

                                    bValue =
                                        b.children[index]
                                            .textContent
                                            .trim();
                                }


                                const aNumber =
                                    parseFloat(
                                        aValue
                                            .replace(
                                                /,/g,
                                                ""
                                            )
                                    );

                                const bNumber =
                                    parseFloat(
                                        bValue
                                            .replace(
                                                /,/g,
                                                ""
                                            )
                                    );


                                let comparison;


                                if (
                                    !isNaN(aNumber)
                                    &&
                                    !isNaN(bNumber)
                                ) {

                                    comparison =
                                        aNumber -
                                        bNumber;

                                } else {

                                    comparison =
                                        aValue.localeCompare(
                                            bValue
                                        );
                                }


                                if (
                                    currentDirection ===
                                    "descending"
                                ) {

                                    comparison *= -1;
                                }


                                return comparison;
                            }
                        );


                        rows.forEach(
                            function(row) {

                                tbody.appendChild(
                                    row
                                );
                            }
                        );

                    }
                );

            }
        );

    }
);

</script>

</body>

</html>
"""


    return html_output


# ============================================================
# MAIN
# ============================================================

def main():

    spreadsheet = get_google_sheet()

    batting_data = get_all_batting_data(
        spreadsheet
    )

    html_output = make_page(
        batting_data
    )


    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            html_output
        )


    print(
        f"Created {OUTPUT_FILE} with "
        f"{len(batting_data)} players."
    )


if __name__ == "__main__":

    main()
