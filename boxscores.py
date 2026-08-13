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
    """
    Read Batting Stats and create a player-name -> position lookup.
    Column B = player name
    Column C = position
    """

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
    """
    Read all batting rows and organize them by game.
    """

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

        # Ignore rows without a game ID
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
            "opponent_display": opponent_code,
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


def print_game(game, batting_rows):

    print()
    print("=" * 70)

    title = (
        f"{game['game_id']} — {game['date']} | "
        f"{game['winner']} {game['winner_runs']}, "
        f"{game['loser']} {game['loser_runs']}"
    )

    print(title)

    if game["note"]:
        print(game["note"])

    print("=" * 70)

    teams = []

        # Team totals
        total_ab = 0
        total_r = 0
        total_h = 0
        total_rbi = 0
        total_bb = 0
        total_k = 0

        for player in batting_rows:

            if player["team_code"] != team_code:
                continue

            batter_display = player["batter"]

            if player["position"]:
                batter_display += f" {player['position']}"

            print(
                f"{player['opponent_display']:<12}"
                f"{batter_display:<22}"
                f"{player['AB']:>4}"
                f"{player['R']:>4}"
                f"{player['H']:>4}"
                f"{player['RBI']:>5}"
                f"{player['BB']:>4}"
                f"{player['K']:>4}"
            )

            # Add this player's statistics to the team totals
            total_ab += int(player["AB"] or 0)
            total_r += int(player["R"] or 0)
            total_h += int(player["H"] or 0)
            total_rbi += int(player["RBI"] or 0)
            total_bb += int(player["BB"] or 0)
            total_k += int(player["K"] or 0)

        print("-" * 65)

        print(
            f"{'Totals':<34}"
            f"{total_ab:>4}"
            f"{total_r:>4}"
            f"{total_h:>4}"
            f"{total_rbi:>5}"
            f"{total_bb:>4}"
            f"{total_k:>4}"
        )

        print("-" * 65)

        for player in batting_rows:

            if player["team_code"] != team_code:
                continue

            batter_display = player["batter"]

            if player["position"]:
                batter_display += f" {player['position']}"

            print(
                f"{player['opponent_display']:<12}"
                f"{batter_display:<22}"
                f"{player['AB']:>4}"
                f"{player['R']:>4}"
                f"{player['H']:>4}"
                f"{player['RBI']:>5}"
                f"{player['BB']:>4}"
                f"{player['K']:>4}"
            )


def main():

    spreadsheet = get_google_sheet()

    standings = spreadsheet.worksheet("Standings")
    batting = spreadsheet.worksheet("Batting")
    batting_stats = spreadsheet.worksheet("Batting Stats")

    games = get_games(standings)

    player_positions = get_player_positions(batting_stats)

    batting_by_game = get_batting_data(
        batting,
        player_positions
    )

    print(f"Found {len(games)} games.")

    for game in games:

        game_id = game["game_id"]

        batting_rows = batting_by_game.get(
            game_id,
            []
        )

        print_game(
            game,
            batting_rows
        )


if __name__ == "__main__":
    main()
