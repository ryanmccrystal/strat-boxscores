import os
import json
import html
import re

import gspread
from google.oauth2.service_account import Credentials


# ============================================================
# SETTINGS
# ============================================================

SPREADSHEET_ID = (
    "1hPnUsWFFjbFQZPrqc2F4X9f4ytjP2zb9sdhp8T0gjN0"
)

OUTPUT_FILE = "batting-stats.html"


# ============================================================
# TEAM TABS
# ============================================================

TEAM_TABS = [
    "Iowa",
    "Omaha",
    "Richmond",
    "Pawtucket",
    "Dunedin",
    "Portland"
    # Add the rest of your team tab names here
]


# ============================================================
# LOGOS
# ============================================================

LOGO_DIRECTORY = "logos"


# ============================================================
# GOOGLE SHEETS
# ============================================================

def get_google_sheet():

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly"
    ]

    credentials_info = json.loads(
        os.environ["GOOGLE_SERVICE_ACCOUNT"]
    )

    credentials = (
        Credentials.from_service_account_info(
            credentials_info,
            scopes=scopes
        )
    )

    client = gspread.authorize(
        credentials
    )

    return client.open_by_key(
        SPREADSHEET_ID
    )


# ============================================================
# HTML ESCAPE
# ============================================================

def html_escape(value):

    return html.escape(
        str(value),
        quote=True
    )


# ============================================================
# GET TEAM DATA
# ============================================================

def get_team_data(
    spreadsheet,
    team_tab
):

    worksheet = spreadsheet.worksheet(
        team_tab
    )

    return worksheet.get_all_values()


# ============================================================
# FIND SECTIONS
# ============================================================

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


# ============================================================
# GET SECTION ROWS
# ============================================================

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

    section = rows[
        start:end
    ]

    while (
        section
        and not any(
            cell.strip()
            for cell in section[0]
        )
    ):

        section.pop(0)

    while (
        section
        and not any(
            cell.strip()
            for cell in section[-1]
        )
    ):

        section.pop()

    return section


# ============================================================
# LOGO MAP
# ============================================================

def get_logo_map(spreadsheet):

    worksheet = spreadsheet.worksheet(
        "Logos"
    )

    rows = worksheet.get(
        "A1:B1500",
        value_render_option="FORMULA"
    )

    logo_map = {}

    for row in rows:

        if len(row) < 2:
            continue

        real_team = str(
            row[0]
        ).strip()

        image_formula = str(
            row[1]
        ).strip()

        if not real_team:
            continue

        if not image_formula.lower().startswith(
            "=image("
        ):
            continue

        start = image_formula.find('"')
        end = image_formula.rfind('"')

        if start == -1 or end <= start:
            continue

        logo_url = image_formula[
            start + 1:end
        ]

        if logo_url:

            logo_map[
                real_team
            ] = logo_url

    return logo_map


# ============================================================
# FIND REAL TM COLUMN
# ============================================================

def find_real_team_column(header):

    for index, value in enumerate(header):

        header_value = (
            value.strip().lower()
        )

        if header_value in (
            "real tm",
            "tm/yr",
            "tm - yr"
        ):

            return index

    return None


# ============================================================
# GET LOGO URL FOR A ROW
# ============================================================

def get_logo_url(
    row,
    real_team_column,
    logo_map
):

    if real_team_column is None:
        return ""

    if real_team_column >= len(row):
        return ""

    real_team = row[
        real_team_column
    ].strip()

    if not real_team:
        return ""

    return logo_map.get(
        real_team,
        ""
    )


# ============================================================
# GET ALL BATTING DATA
# ============================================================

def get_all_batting_data(
    spreadsheet
):

    logo_map = get_logo_map(
        spreadsheet
    )

    all_players = []

    for team_tab in TEAM_TABS:

        print(
            f"Reading batting stats: {team_tab}"
        )

        rows = get_team_data(
            spreadsheet,
            team_tab
        )

        sections = find_section_rows(
            rows
        )

        if "Batting" not in sections:

            print(
                f"WARNING: No Batting section "
                f"found for {team_tab}"
            )

            continue


        ordered_sections = sorted(
            sections.items(),
            key=lambda item: item[1]
        )


        batting_start = sections[
            "Batting"
        ]


        next_start = None

        for section_name, start in (
            ordered_sections
        ):

            if start > batting_start:

                next_start = start

                break


        section_rows = get_section_rows(
            rows,
            batting_start,
            next_start
        )


        if len(section_rows) < 2:

            continue


        header = section_rows[0]

        data_rows = section_rows[1:]


        # Find the final used column.
        last_column = 0

        for row in section_rows:

            for index, value in enumerate(row):

                if value.strip():

                    last_column = max(
                        last_column,
                        index
                    )


        header = header[
            :last_column + 1
        ]


        real_team_column = (
            find_real_team_column(
                header
            )
        )


        for row in data_rows:

            row = row[
                :last_column + 1
            ]


            if not any(
                value.strip()
                for value in row
            ):

                continue


            # Do not include Team Totals.
            if any(
                value.strip() == "Team"
                for value in row
            ):

                continue


            # Make sure there is a player name.
            if len(row) < 2:

                continue


            player_name = row[
                1
            ].strip()


            if not player_name:

                continue


            logo_url = get_logo_url(
                row,
                real_team_column,
                logo_map
            )


            all_players.append(
                {
                    "team": team_tab,
                    "header": header,
                    "row": row,
                    "logo_url": logo_url
                }
            )


    return all_players


# ============================================================
# MAKE TABLE
# ============================================================

def make_batting_table(
    players
):

    if not players:

        return """
        <p>No batting data found.</p>
        """


    header = players[0]["header"]


    html_output = """
    <div class="table-wrapper">

        <table
            class="batting-stats-table"
            id="batting-stats-table"
        >

            <thead>

                <tr>

                    <th
                        class="sortable team-column"
                        data-column="team"
                    >
                        Team
                    </th>
    """


    # Column A is the spreadsheet logo column.
    # Start with the actual spreadsheet headers
    # beginning with Column B.
    for index, value in enumerate(
        header[1:],
        start=1
    ):

        if not value.strip():

            continue

        html_output += f"""
                    <th
                        class="sortable"
                        data-column="{index}"
                    >
                        {html_escape(value)}
                    </th>
        """


    html_output += """
                </tr>

            </thead>

            <tbody>
    """


    for player in players:

        row = player["row"]

        logo_url = player["logo_url"]


        html_output += """
                <tr>
        """


        # Team column.
        html_output += f"""
                    <td class="team-column">
                        {html_escape(player["team"])}
                    </td>
        """


        # Spreadsheet columns B onward.
        for column_index, value in enumerate(
            row[1:],
            start=1
        ):

            # Don't allow the logo formula itself
            # to appear as text.
            if column_index == 0:

                continue


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

    </div>
    """


    return html_output


# ============================================================
# PAGE
# ============================================================

def make_page(
    players
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

        font-weight: 700;

        margin: 0 0 20px 0;
    }


    .table-wrapper {

        width: 100%;

        overflow-x: auto;
    }


    .batting-stats-table {

        width: 100%;

        border-collapse: collapse;

        table-layout: auto;

        font-size: 14px;

        white-space: nowrap;
    }


    .batting-stats-table th,
    .batting-stats-table td {

        padding: 4px 7px;

        text-align: center;

        line-height: 1.15;
    }


    .batting-stats-table th {

        font-weight: 700;

        background: #f2f2f2;

        border-bottom: 1px solid #222;

        cursor: pointer;

        user-select: none;
    }


    .batting-stats-table td {

        border-bottom: 1px solid #dddddd;
    }


    .batting-stats-table
    th.team-column,
    .batting-stats-table
    td.team-column {

        text-align: left;

        font-weight: 600;
    }


    .batting-stats-table
    tbody tr:hover {

        background: #f5f5f5;
    }


    .sortable::after {

        content: " ↕";

        font-size: 10px;

        color: #888;
    }


    .sortable.sort-ascending::after {

        content: " ▲";

        color: #111;
    }


    .sortable.sort-descending::after {

        content: " ▼";

        color: #111;
    }


    @media (max-width: 900px) {

        body {

            padding: 15px;
        }


        .batting-stats-table {

            font-size: 13px;
        }


        .batting-stats-table th,
        .batting-stats-table td {

            padding: 3px 5px;
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
        players
    )


    html_output += """

</div>


<script>

document.addEventListener(
    "DOMContentLoaded",
    function() {

        const table =
            document.getElementById(
                "batting-stats-table"
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


                        const descending =
                            header.classList.contains(
                                "sort-ascending"
                            );


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
                            descending
                                ? "sort-descending"
                                : "sort-ascending"
                        );


                        rows.sort(
                            function(a, b) {

                                const index =
                                    column === "team"
                                        ? 0
                                        : parseInt(
                                            column
                                        );


                                let aValue =
                                    a.children[
                                        index
                                    ].textContent.trim();

                                let bValue =
                                    b.children[
                                        index
                                    ].textContent.trim();


                                const aNumber =
                                    parseFloat(
                                        aValue.replace(
                                            /,/g,
                                            ""
                                        )
                                    );

                                const bNumber =
                                    parseFloat(
                                        bValue.replace(
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


                                if (descending) {

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

    players = get_all_batting_data(
        spreadsheet
    )

    html_output = make_page(
        players
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
        f"{len(players)} players."
    )


if __name__ == "__main__":

    main()
