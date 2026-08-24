import os
import json
import html

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

# KEEP THE SAME TEAM_TABS LIST FROM YOUR
# CURRENT WORKING batting-stats.py HERE.

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
#
# Logos tab:
#
# Column A = Tm/Yr
# Column B = IMAGE("URL")
# ============================================================

def get_logo_map(
    spreadsheet
):

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


        team_year = str(
            row[0]
        ).strip()


        image_formula = str(
            row[1]
        ).strip()


        if not team_year:

            continue


        if not image_formula.lower().startswith(
            "=image("
        ):

            continue


        start = image_formula.find(
            '"'
        )

        end = image_formula.rfind(
            '"'
        )


        if (
            start == -1
            or end <= start
        ):

            continue


        logo_url = image_formula[
            start + 1:end
        ]


        if logo_url:

            logo_map[
                team_year
            ] = logo_url


    return logo_map


# ============================================================
# FIND TM/YR COLUMN
# ============================================================

def find_tm_year_column(
    header
):

    for index, value in enumerate(
        header
    ):

        header_value = (
            value.strip().lower()
        )


        if header_value in (
            "tm/yr",
            "real tm",
            "tm - yr"
        ):

            return index


    return None


# ============================================================
# GET LOGO FOR PLAYER
#
# IMPORTANT:
# Logo is determined from the player's
# Tm/Yr value.
# ============================================================

def get_logo_url(
    row,
    tm_year_column,
    logo_map
):

    if tm_year_column is None:

        return ""


    if tm_year_column >= len(row):

        return ""


    team_year = row[
        tm_year_column
    ].strip()


    if not team_year:

        return ""


    return logo_map.get(
        team_year,
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


        for (
            section_name,
            start
        ) in ordered_sections:

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


        # Find the last column actually
        # containing data.

        last_column = 0


        for row in section_rows:

            for index, value in enumerate(
                row
            ):

                if value.strip():

                    last_column = max(
                        last_column,
                        index
                    )


        header = header[
            :last_column + 1
        ]


        # Find the Tm/Yr column.

        tm_year_column = (
            find_tm_year_column(
                header
            )
        )


        # ----------------------------------------------------
        # PLAYER ROWS
        # ----------------------------------------------------

        for row in data_rows:

            row = row[
                :last_column + 1
            ]


            if not any(
                value.strip()
                for value in row
            ):

                continue


            # Column B is the player name.
            #
            # Exclude Team Totals specifically.

            if len(row) > 1:

                if row[1].strip() == "Team Totals":

                    continue


            # Make sure Column B exists.

            if len(row) < 2:

                continue


            player_name = row[
                1
            ].strip()


            if not player_name:

                continue


            # Find logo using Tm/Yr.

            logo_url = get_logo_url(
                row,
                tm_year_column,
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
# MAKE BATTING TABLE
#
# Columns:
#
# Team | Logo | Player | Tm/Yr | remaining stats
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
                        data-sort-column="team"
                    >
                        Team
                    </th>


                    <th class="logo-column">
                        Logo
                    </th>
    """


    # --------------------------------------------------------
    # Spreadsheet headers.
    #
    # Column A is the existing logo column in the
    # spreadsheet, so we skip it.
    #
    # Column B onward contains the actual batting data.
    # --------------------------------------------------------

    for column_index, value in enumerate(
        header[1:],
        start=2
    ):

        if not value.strip():

            continue


        html_output += f"""
                    <th
                        class="sortable"
                        data-sort-column="{column_index}"
                    >
                        {html_escape(value)}
                    </th>
        """


    html_output += """
                </tr>

            </thead>

            <tbody>
    """


    # ========================================================
    # PLAYER ROWS
    # ========================================================

    for player in players:

        row = player["row"]

        logo_url = player["logo_url"]


        html_output += """
                <tr>
        """


        # ----------------------------------------------------
        # TEAM
        # ----------------------------------------------------

        html_output += f"""
                    <td class="team-column">
                        {html_escape(player["team"])}
                    </td>
        """


        # ----------------------------------------------------
        # LOGO
        # ----------------------------------------------------

        if logo_url:

            html_output += f"""
                    <td class="logo-column">

                        <img
                            src="{html_escape(logo_url)}"
                            class="team-logo"
                            alt=""
                        >

                    </td>
            """

        else:

            html_output += """
                    <td class="logo-column"></td>
            """


        # ----------------------------------------------------
        # PLAYER + REMAINING DATA
        #
        # row[1] = Player
        # row[2] = Tm/Yr / Real Tm
        # row[3] onward = remaining batting stats
        # ----------------------------------------------------

        for value in row[1:]:

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

<title>
    Batting Stats - Strat-o-Matic
</title>


<link
    rel="preconnect"
    href="https://fonts.googleapis.com"
>


<link
    rel="preconnect"
    href="https://fonts.googleapis.com"
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


    .batting-stats-table
    th.logo-column {

        cursor: default;
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


    .logo-column {

        width: 35px;
    
        min-width: 35px;
    
        max-width: 35px;
    
        text-align: center !important;
    
        padding-left: 3px !important;
    
        padding-right: 3px !important;
    }
    
    
    .team-logo {
    
        width: 25px;
    
        height: 25px;
    
        object-fit: contain;
    
        display: block;
    
        margin: 0 auto;
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


        .team-logo {

            width: 25px;

            height: 25px;
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

                        const sortColumn =
                            header.dataset.sortColumn;


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


                        const currentlyAscending =
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
                            currentlyAscending
                                ? "sort-descending"
                                : "sort-ascending"
                        );


                        rows.sort(
                            function(a, b) {

                                let aValue;
                                let bValue;


                                // Team is a special
                                // non-spreadsheet column.

                                if (
                                    sortColumn === "team"
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
                                            sortColumn
                                        );


                                    // Spreadsheet
                                    // Column B is
                                    // HTML column 2
                                    // because Team
                                    // and Logo were
                                    // inserted first.

                                    const htmlIndex =
                                        index + 1;


                                    aValue =
                                        a.children[
                                            htmlIndex
                                        ]
                                            .textContent
                                            .trim();

                                    bValue =
                                        b.children[
                                            htmlIndex
                                        ]
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
                                    currentlyAscending
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
        f"Created {OUTPUT_FILE} "
        f"with {len(players)} players."
    )


if __name__ == "__main__":

    main()
