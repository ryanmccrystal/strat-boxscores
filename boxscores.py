import os
import json
import re
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1hPnUsWFFjbFQZPrqc2F4X9f4ytjP2zb9sdhp8T0gjN0"

TEAM_NAMES = {
    "PDX": "Portland",
    "IOWA": "Iowa",
    "PAW": "Pawtucket",
    "RICH": "Richmond",
    "OMA": "Omaha",
    "DUNE": "Dunedin",
}


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


def game_number(game_id):
    match = re.search(r"\d+", game_id)

    if match:
        return int(match.group())

    return 999999


def get_games(standings):
    rows = standings.get_all_values()

    games = []

    for row in rows[1:]:

        if len(row) < 17:
            continue

        game_id = row[10].strip()

        if not game_id.startswith("Gm"):
            continue

        games.append({
            "game_id": game_id,
            "date": row[11].strip(),
            "winner": row[12].strip(),
            "winner_runs": row[13].strip(),
            "loser": row[14].strip(),
            "loser_runs": row[15].strip(),
            "note": row[16].strip(),
        })

    games.sort(key=lambda x: game_number(x["game_id"]))

    return games


def get_player_positions(batting_stats):
    rows = batting_stats.get_all_values()

    positions = {}

    for row in rows[1:]:

        if len(row) < 3:
            continue

        player_name = row[1].strip()
        position = row[2].strip()

        if player_name:
            positions[player_name] = position

    return positions


def get_batting_data(batting, player_positions):
    rows = batting.get_all_values()

    batting_by_game = {}

    for row in rows[1:]:

        if len(row) < 28:
            continue

        team_code = row[0].strip()
        opponent_code = row[1].strip()
        batter = row[2].strip()
        pa = row[4].strip()
        game_id = row[27].strip()

        if not game_id:
            continue

        if pa == "0":
            continue

        position = player_positions.get(batter, "")

        player = {
            "team_code": team_code,
            "team": TEAM_NAMES.get(team_code, team_code),
            "opponent_code": opponent_code,
            "opponent": TEAM_NAMES.get(
                opponent_code,
                opponent_code
            ),
            "batter": batter,
            "position": position,
            "AB": row[5].strip(),
            "R": row[6].strip(),
            "H": row[7].strip(),
            "RBI": row[8].strip(),
            "BB": row[9].strip(),
            "K": row[10].strip(),

            # Notes section
            "2B": row[11].strip(),
            "3B": row[12].strip(),
            "HR": row[13].strip(),
            "SB": row[14].strip(),
            "CS": row[15].strip(),
            "GIDP": row[16].strip(),
            "SF": row[17].strip(),
            "E": row[20].strip(),
            "SH": row[29].strip(),
        }

        if game_id not in batting_by_game:
            batting_by_game[game_id] = []

        batting_by_game[game_id].append(player)

    return batting_by_game


def get_pitching_data(pitching):
    """
    Read the Pitching tab.

    Columns:
    A = Pitcher
    B = Team
    C = Opponent
    D = SP?
    E = IP
    F = BF
    G = H
    H = R
    I = ER
    J = BB
    K = K
    L = W
    M = L
    N = H
    O = S
    P = BS
    """

    rows = pitching.get_all_values()

    pitching_by_game = {}

    for row in rows[1:]:

        if len(row) < 16:
            continue

        pitcher = row[0].strip()
        team_code = row[1].strip()
        opponent_code = row[2].strip()
        game_id = row[30].strip() if len(row) > 30 else ""

        if not pitcher or not game_id:
            continue

        pitcher_data = {
            "pitcher": pitcher,
            "team_code": team_code,
            "team": TEAM_NAMES.get(team_code, team_code),
            "opponent_code": opponent_code,
            "opponent": TEAM_NAMES.get(
                opponent_code,
                opponent_code
            ),
            "IP": row[4].strip(),
            "R": row[7].strip(),
            "ER": row[8].strip(),
            "BB": row[9].strip(),
            "K": row[10].strip(),
            "W": row[11].strip(),
            "L": row[12].strip(),
            "HLD": row[13].strip(),
            "SV": row[14].strip(),
            "BS": row[15].strip(),
        }

        if game_id not in pitching_by_game:
            pitching_by_game[game_id] = []

        pitching_by_game[game_id].append(pitcher_data)

    return pitching_by_game


def make_totals(players):

    total_ab = 0
    total_r = 0
    total_h = 0
    total_rbi = 0
    total_bb = 0
    total_k = 0

    for player in players:

        total_ab += int(player["AB"] or 0)
        total_r += int(player["R"] or 0)
        total_h += int(player["H"] or 0)
        total_rbi += int(player["RBI"] or 0)
        total_bb += int(player["BB"] or 0)
        total_k += int(player["K"] or 0)

    return {
        "AB": total_ab,
        "R": total_r,
        "H": total_h,
        "RBI": total_rbi,
        "BB": total_bb,
        "K": total_k,
    }


def html_escape(value):
    value = str(value)

    return (
        value
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def make_team_section(team_code, players):

    team_name = TEAM_NAMES.get(team_code, team_code)

    team_players = [
        player
        for player in players
        if player["team_code"] == team_code
    ]

    totals = make_totals(team_players)

    html = f"""
    <section class="team-section">

        <h2>{html_escape(team_name)}</h2>

        <table class="batting-table">

            <thead>
                <tr>
                    <th class="player-column"></th>
                    <th>AB</th>
                    <th>R</th>
                    <th>H</th>
                    <th>BI</th>
                    <th>BB</th>
                    <th>K</th>
                </tr>
            </thead>

            <tbody>
    """

    for player in team_players:

        batter_name = html_escape(player["batter"])
        position = html_escape(player["position"])

        if position:
            display_name = f"{batter_name} {position}"
        else:
            display_name = batter_name

        html += f"""
                <tr>
                    <td class="player-name">{display_name}</td>
                    <td>{html_escape(player["AB"])}</td>
                    <td>{html_escape(player["R"])}</td>
                    <td>{html_escape(player["H"])}</td>
                    <td>{html_escape(player["RBI"])}</td>
                    <td>{html_escape(player["BB"])}</td>
                    <td>{html_escape(player["K"])}</td>
                </tr>
        """

    html += f"""
                <tr class="totals">
                    <td class="player-name">Totals</td>
                    <td>{totals["AB"]}</td>
                    <td>{totals["R"]}</td>
                    <td>{totals["H"]}</td>
                    <td>{totals["RBI"]}</td>
                    <td>{totals["BB"]}</td>
                    <td>{totals["K"]}</td>
                </tr>
            </tbody>

        </table>

    </section>
    """

    return html


def get_pitcher_decision(pitcher):
    """
    Determine the current game's decision.

    Priority:
    W, L, HLD, SV, BS
    """

    if pitcher["W"]:
        return "W"

    if pitcher["L"]:
        return "L"

    if pitcher["HLD"]:
        return "H"

    if pitcher["SV"]:
        return "S"

    if pitcher["BS"]:
        return "BS"

    return ""


def update_pitcher_record(records, pitcher, decision):
    """
    Update the season-to-date record for a pitcher.
    """

    if pitcher not in records:

        records[pitcher] = {
            "W": 0,
            "L": 0,
            "H": 0,
            "S": 0,
            "BS": 0,
        }

    if decision == "W":
        records[pitcher]["W"] += 1

    elif decision == "L":
        records[pitcher]["L"] += 1

    elif decision == "H":
        records[pitcher]["H"] += 1

    elif decision == "S":
        records[pitcher]["S"] += 1

    elif decision == "BS":
        records[pitcher]["BS"] += 1


def pitcher_display_name(pitcher, decision, records):

    name = html_escape(pitcher["pitcher"])

    # Make sure this pitcher has a season record
    # before we try to display it.
    if pitcher["pitcher"] not in records:
        records[pitcher["pitcher"]] = {
            "W": 0,
            "L": 0,
            "H": 0,
            "S": 0,
            "BS": 0,
        }

    if not decision:
        return name

    record = records[pitcher["pitcher"]]

    if decision == "W":
        return f"{name} W, {record['W'] + 1}-{record['L']}"

    if decision == "L":
        return f"{name} L, {record['W']}-{record['L'] + 1}"

    if decision == "H":
        return f"{name} H, {record['H'] + 1}"

    if decision == "S":
        return f"{name} S, {record['S'] + 1}"

    if decision == "BS":
        return f"{name} BS, {record['BS'] + 1}"

    return name

def get_note_season_totals(games, batting_by_game):
    """
    Calculate season-to-date totals for:
    E, 2B, 3B, HR, SB, CS

    The current game is included in the total.
    """

    season_totals = {}

    for game in games:

        game_id = game["game_id"]

        players = batting_by_game.get(
            game_id,
            []
        )

        for player in players:

            player_name = player["batter"]

            if player_name not in season_totals:
                season_totals[player_name] = {
                    "E": 0,
                    "2B": 0,
                    "3B": 0,
                    "HR": 0,
                    "SB": 0,
                    "CS": 0,
                }

            for category in [
                "E",
                "2B",
                "3B",
                "HR",
                "SB",
                "CS",
            ]:

                value = player[category]

                if value:
                    season_totals[player_name][category] += int(
                        value
                    )

        # Store a snapshot for this game.
        game["note_season_totals"] = {
            player_name: totals.copy()
            for player_name, totals in season_totals.items()
        }

    return season_totals

def make_notes_section(
    batting_rows,
    season_totals
):
    """
    Create the compact Notes paragraph.
    """

    categories_with_totals = [
        ("E", "E"),
        ("2B", "2B"),
        ("3B", "3B"),
        ("HR", "HR"),
        ("SB", "SB"),
        ("CS", "CS"),
    ]

    categories_without_totals = [
        ("GIDP", "GIDP"),
        ("SH", "SH"),
        ("SF", "SF"),
    ]

    parts = []

    # Categories with season totals
    for category, label in categories_with_totals:

        events = []

        for player in batting_rows:

            value = player[category]

            if not value:
                continue

            try:
                count = int(value)
            except ValueError:
                continue

            if count <= 0:
                continue

            player_name = html_escape(
                player["batter"]
            )

            totals = season_totals.get(
                player["batter"],
                {}
            )

            season_total = totals.get(
                category,
                count
            )

            events.append(
                f"{player_name} ({season_total})"
            )

        if events:

            parts.append(
                f"<strong>{label}:</strong> "
                + ", ".join(events)
                + "."
            )

    # Categories without season totals
    for category, label in categories_without_totals:

        events = []

        for player in batting_rows:

            value = player[category]

            if not value:
                continue

            try:
                count = int(value)
            except ValueError:
                continue

            if count <= 0:
                continue

            events.append(
                html_escape(player["batter"])
            )

        if events:

            parts.append(
                f"<strong>{label}:</strong> "
                + ", ".join(events)
                + "."
            )

    if not parts:
        return ""

    return f"""
    <div class="notes">
        {" ".join(parts)}
    </div>
    """

def make_pitching_section(team_code, pitchers, records):

    team_name = TEAM_NAMES.get(team_code, team_code)

    team_pitchers = [
        pitcher
        for pitcher in pitchers
        if pitcher["team_code"] == team_code
    ]

    html = f"""
    <section class="pitching-section">

        <h3>{html_escape(team_name)} Pitching</h3>

        <table class="pitching-table">

            <thead>
                <tr>
                    <th class="pitcher-column"></th>
                    <th>IP</th>
                    <th>R</th>
                    <th>ER</th>
                    <th>BB</th>
                    <th>K</th>
                </tr>
            </thead>

            <tbody>
    """

    for pitcher in team_pitchers:

        decision = get_pitcher_decision(pitcher)

        display_name = pitcher_display_name(
            pitcher,
            decision,
            records
        )

        html += f"""
                <tr>
                    <td class="pitcher-name">{display_name}</td>
                    <td>{html_escape(pitcher["IP"])}</td>
                    <td>{html_escape(pitcher["R"])}</td>
                    <td>{html_escape(pitcher["ER"])}</td>
                    <td>{html_escape(pitcher["BB"])}</td>
                    <td>{html_escape(pitcher["K"])}</td>
                </tr>
        """

    html += """
            </tbody>

        </table>

    </section>
    """

    return html


def make_game_section(
    game,
    batting_rows,
    pitching_rows,
    records
):

    teams = []

    for player in batting_rows:

        if player["team_code"] not in teams:
            teams.append(player["team_code"])

    for pitcher in pitching_rows:

        if pitcher["team_code"] not in teams:
            teams.append(pitcher["team_code"])

    winner = html_escape(game["winner"])
    loser = html_escape(game["loser"])

    winner_runs = html_escape(game["winner_runs"])
    loser_runs = html_escape(game["loser_runs"])

    html = f"""
    <article class="game">

        <div class="game-header">

            <div class="score">
                <strong>{winner} {winner_runs}, {loser} {loser_runs}</strong>
            </div>

            <div class="game-info">
                {html_escape(game["game_id"])}
                &nbsp; | &nbsp;
                {html_escape(game["date"])}
            </div>
    """

    if game["note"]:

        html += f"""
            <div class="game-note">
                {html_escape(game["note"])}
            </div>
        """

    html += """
        </div>
    """

    for team_code in teams:

        html += make_team_section(
            team_code,
            batting_rows
        )

    # Notes section
    note_season_totals = game.get(
        "note_season_totals",
        {}
    )

    notes_html = make_notes_section(
        batting_rows,
        note_season_totals
    )

    html += notes_html

    # Add pitching sections
    for team_code in teams:

        html += make_pitching_section(
            team_code,
            pitching_rows,
            records
        )

    html += """
    </article>
    """

    return html


def create_html(
    games,
    batting_by_game,
    pitching_by_game
):

    html = """<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Strat-o-Matic Box Scores</title>

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">

<style>

    body {
        font-family: "Source Sans 3", Arial, Helvetica, sans-serif;
        background: #ffffff;
        color: #111111;
        margin: 0;
        padding: 20px;
    }

    .container {
        max-width: 1800px;
        margin: 0 auto;
    }

    h1 {
        font-size: 24px;
        margin: 0 0 20px 0;
    }

    .games-grid {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 16px;
        align-items: start;
    }

    .game {
        margin: 0;
        padding: 10px;
        border: 1px solid #222;
        font-size: 10px;
        min-width: 0;
    }

    .game-header {
        margin-bottom: 10px;
    }

    .score {
        font-size: 14px;
        margin-bottom: 2px;
        line-height: 1.2;
    }

    .game-info {
        font-size: 9px;
        color: #666;
        line-height: 1.2;
    }

    .game-note {
        font-size: 9px;
        font-weight: bold;
        margin-top: 2px;
    }

    .team-section {
        margin-top: 10px;
    }

    .team-section h2 {
        font-size: 12px;
        margin: 0 0 3px 0;
    }

    .batting-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 9px;
    }

    .batting-table th {
        font-weight: normal;
        border-bottom: 1px solid #222;
        padding: 2px 2px;
        text-align: right;
    }

    .batting-table th.player-column {
        text-align: left;
    }

    .batting-table td {
        padding: 2px 2px;
        text-align: right;
        line-height: 1.15;
    }

    .batting-table td.player-name {
        text-align: left;
        white-space: nowrap;
    }

    .batting-table tr.totals {
        border-top: 1px solid #222;
        font-weight: bold;
    }

    .notes {
        margin-top: 10px;
        margin-bottom: 10px;
        font-size: 9px;
        line-height: 1.35;
    }

    .pitching-section {
        margin-top: 10px;
    }

    .pitching-section h3 {
        font-size: 12px;
        margin: 0 0 3px 0;
    }

    .pitching-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 9px;
    }

    .pitching-table th {
        font-weight: normal;
        border-bottom: 1px solid #222;
        padding: 2px 2px;
        text-align: right;
    }

    .pitching-table th.pitcher-column {
        text-align: left;
    }

    .pitching-table td {
        padding: 2px 2px;
        text-align: right;
        line-height: 1.15;
    }

    .pitching-table td.pitcher-name {
        text-align: left;
        white-space: nowrap;
    }

    @media (max-width: 1400px) {

        .games-grid {
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }

    }

    @media (max-width: 1150px) {

        .games-grid {
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }

    }

    @media (max-width: 850px) {

        body {
            padding: 12px;
        }

        .games-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

    }

    @media (max-width: 600px) {

        body {
            padding: 10px;
        }

        .games-grid {
            grid-template-columns: 1fr;
        }

        .game {
            padding: 12px;
            font-size: 12px;
        }

        .score {
            font-size: 17px;
        }

        .game-info {
            font-size: 11px;
        }

        .team-section h2,
        .pitching-section h3 {
            font-size: 14px;
        }

        .batting-table,
        .pitching-table {
            font-size: 12px;
        }

        .batting-table th,
        .batting-table td,
        .pitching-table th,
        .pitching-table td {
            padding: 3px;
        }

        .notes {
            font-size: 11px;
        }

    }

</style>

</head>

<body>

<div class="container">

<h1>Strat-o-Matic Box Scores</h1>

<div class="games-grid">
"""

    # Calculate season-to-date batting note totals.
    get_note_season_totals(
        games,
        batting_by_game
    )

    # Tracks season-to-date pitching records.
    records = {}

    for game in games:

        game_id = game["game_id"]

        batting_rows = batting_by_game.get(
            game_id,
            []
        )

        pitching_rows = pitching_by_game.get(
            game_id,
            []
        )

        # Generate this game's box score.
        html += make_game_section(
            game,
            batting_rows,
            pitching_rows,
            records
        )

        # Update pitcher records AFTER generating
        # the current game's box score.
        for pitcher in pitching_rows:

            decision = get_pitcher_decision(
                pitcher
            )

            if decision:

                update_pitcher_record(
                    records,
                    pitcher["pitcher"],
                    decision
                )

    html += """
</div>

</div>

</body>

</html>
"""

    return html

def main():

    spreadsheet = get_google_sheet()

    standings = spreadsheet.worksheet("Standings")
    batting = spreadsheet.worksheet("Batting")
    batting_stats = spreadsheet.worksheet("Batting Stats")
    pitching = spreadsheet.worksheet("Pitching")

    games = get_games(standings)

    player_positions = get_player_positions(
        batting_stats
    )

    batting_by_game = get_batting_data(
        batting,
        player_positions
    )

    pitching_by_game = get_pitching_data(
        pitching
    )

    html = create_html(
        games,
        batting_by_game,
        pitching_by_game
    )

    with open(
        "boxscores.html",
        "w",
        encoding="utf-8"
    ) as file:

        file.write(html)

    print(
        f"Created boxscores.html with {len(games)} games."
    )


if __name__ == "__main__":
    main()
