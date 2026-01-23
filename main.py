import argparse
import os.path
import random

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
NAMES_TICKETS_RANGE = "A2:B"


class Raffle:
    def __init__(self, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self._sheet = None

    @property
    def sheet(self):
        if self._sheet is None:
            self._sheet = self._authorize_and_build()
        return self._sheet

    def _authorize(self) -> Credentials:
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())

        return creds

    def _build_service(self, creds: Credentials):
        return build("sheets", "v4", credentials=creds)

    def _authorize_and_build(self):
        creds = self._authorize()
        service = self._build_service(creds)
        return service.spreadsheets()

    def _get_participants(self) -> list[list[str]]:
        result = (
            self.sheet.values()
            .get(spreadsheetId=self.spreadsheet_id, range=NAMES_TICKETS_RANGE)
            .execute()
        )
        return result.get("values", [])

    def _total_tickets(self, participants: list[list[str]]) -> int:
        total_count = 0
        for participant in participants:
            total_count += int(participant[1])
        return total_count

    def _create_row_definition(self, participants: list[list[str]]) -> str:
        total_count = self._total_tickets(participants)
        return f"D2:D{total_count + 1}"

    def _create_entries(self, participants: list[list[str]]) -> list[list[str]]:
        entries = []
        for participant in participants:
            name = participant[0]
            ticket_count = int(participant[1])
            for _ in range(ticket_count):
                entries.append([name])

        random.shuffle(entries)
        return entries

    def _write_entries(self, row_def: str, entries: list[list[str]]) -> None:
        self.sheet.values().update(
            spreadsheetId=self.spreadsheet_id,
            range=row_def,
            body={"values": entries},
            valueInputOption="RAW"
        ).execute()

    def _select_winner(self, participants: list[list[str]]) -> str:
        winning_row = random.randint(2, self._total_tickets(participants) + 1)
        winning_range = f"D{winning_row}"

        result = (
            self.sheet.values()
            .get(spreadsheetId=self.spreadsheet_id, range=winning_range)
            .execute()
        )

        winner = result.get("values", [])
        return winner[0][0] if winner else "Unknown"

    def run(self) -> None:
        """Runs the raffle using participant data from a Google Sheet."""
        try:
            participants = self._get_participants()

            if not participants:
                print("No data found.")
                return

            total = self._total_tickets(participants)
            print(f"Loaded {len(participants)} participants with {total} total tickets.")

            row_def = self._create_row_definition(participants)
            entries = self._create_entries(participants)

            self._write_entries(row_def, entries)

            winner = self._select_winner(participants)

            print(f"Winner is: {winner}!")
        except HttpError as err:
            print(err)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a raffle from a Google Sheet")
    parser.add_argument("spreadsheet_id", help="The Google Spreadsheet ID")
    args = parser.parse_args()

    raffle = Raffle(args.spreadsheet_id)
    raffle.run()
