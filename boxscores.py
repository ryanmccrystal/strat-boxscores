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

        game = {
            "game_id": game_id,
            "date": row[11].strip(),
            "winner": row[12].strip(),
            "winner_runs": row[13].strip(),
            "loser": row[14].strip(),
            "loser_runs": row[15].strip(),
            "note": row[16].strip(),
        }

        games.append(game)

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

        # Ignore players with 0 PA
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
        }

        if game_id not in batting_by_game:
            batting_by_game[game_id] = []

        batting_by_game[game_id].append(player)

    return batting_by_game


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
    """Safely escape text before putting it into HTML."""
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


def make_game_section(game, batting_rows):

    # Find teams in the order they appear in the batting data.
    teams = []

    for player in batting_rows:

        if player["team_code"] not in teams:
            teams.append(player["team_code"])

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
                {html_escape(game["game_id"])} &nbsp; | &nbsp; {html_escape(game["date"])}
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

    html += """
    </article>
    """

    return html


def create_html(games, batting_by_game):

    html = """<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Strat-o-Matic Box Scores</title>

<style>

    body {
        font-family: Arial, Helvetica, sans-serif;
        background: #ffffff;
        color: #111111;
        margin: 0;
        padding: 30px;
    }

    .container {
        max-width: 700px;
        margin: 0 auto;
    }

    h1 {
        font-size: 26px;
        margin-bottom: 30px;
    }

    .game {
        margin-bottom: 45px;
        padding-bottom: 25px;
        border-bottom: 2px solid #222;
    }

    .game-header {
        margin-bottom: 15px;
    }

    .score {
        font-size: 20px;
        margin-bottom: 4px;
    }

    .game-info {
        font-size: 13px;
        color: #666;
    }

    .game-note {
        font-size: 13px;
        font-weight: bold;
        margin-top: 4px;
    }

    .team-section {
        margin-top: 18px;
    }

    .team-section h2 {
        font-size: 17px;
        margin: 0 0 5px 0;
    }

    .batting-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }

    .batting-table th {
        font-weight: normal;
        border-bottom: 1px solid #222;
        padding: 3px 5px;
        text-align: right;
    }

    .batting-table th.player-column {
        text-align: left;
    }

    .batting-table td {
        padding: 3px 5px;
        text-align: right;
    }

    .batting-table td.player-name {
        text-align: left;
        white-space: nowrap;
    }

    .batting-table tr.totals {
        border-top: 1px solid #222;
        font-weight: bold;
    }

    @media (max-width: 600px) {

        body {
            padding: 15px;
        }

        .batting-table {
            font-size: 13px;
        }

        .batting-table th,
        .batting-table td {
            padding: 3px;
        }
    }

</style>

</head>

<body>

<div class="container">

<h1>Strat-o-Matic Box Scores</h1>
"""

    for game in games:

        game_id = game["game_id"]

        batting_rows = batting_by_game.get(
            game_id,
            []
        )

        html += make_game_section(
            game,
            batting_rows
        )

    html += """
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

    games = get_games(standings)

    player_positions = get_player_positions(
        batting_stats
    )

    batting_by_game = get_batting_data(
        batting,
        player_positions
    )

    html = create_html(
        games,
        batting_by_game
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
