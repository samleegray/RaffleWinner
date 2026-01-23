import logging
import os.path
import random
import re
from dataclasses import dataclass

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
NAMES_TICKETS_RANGE = "A2:B"

logger = logging.getLogger(__name__)


class RaffleError(Exception):
    """Base exception for raffle errors."""


class CredentialsError(RaffleError):
    """Missing or invalid credentials."""


class SpreadsheetError(RaffleError):
    """Invalid spreadsheet ID or access error."""


@dataclass
class Participant:
    """Represents a raffle participant with their name and ticket count."""
    name: str
    tickets: int


class Raffle:
    """Runs a lottery/raffle system using Google Sheets as the data source.

    Reads participant names and ticket counts from a spreadsheet, creates a
    weighted random selection based on ticket counts, and picks a winner.
    """

    # Google Spreadsheet IDs are 44 characters, alphanumeric with hyphens/underscores
    SPREADSHEET_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{44}$")

    def __init__(self, spreadsheet_id: str):
        self._validate_spreadsheet_id(spreadsheet_id)
        self.spreadsheet_id = spreadsheet_id
        self._sheet = None

    def _validate_spreadsheet_id(self, spreadsheet_id: str) -> None:
        """Validate that the spreadsheet ID has the expected format."""
        if not self.SPREADSHEET_ID_PATTERN.match(spreadsheet_id):
            raise SpreadsheetError(
                f"Invalid spreadsheet ID format: '{spreadsheet_id}'. "
                "Expected 44 characters (alphanumeric, hyphens, underscores). "
                "Find the ID in the URL: https://docs.google.com/spreadsheets/d/<ID>/edit"
            )

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
                if not os.path.exists("credentials.json"):
                    raise CredentialsError(
                        "credentials.json not found. "
                        "Please download OAuth credentials from Google Cloud Console: "
                        "https://console.cloud.google.com/apis/credentials"
                    )
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

    def _validate_participant(self, row: list[str], row_num: int) -> Participant | None:
        """Validate and convert a spreadsheet row to a Participant.

        Args:
            row: Raw row data from spreadsheet [name, tickets]
            row_num: Row number for error messages

        Returns:
            Participant if valid, None if row should be skipped

        Raises:
            ValueError: If ticket count is not a valid integer
        """
        # Skip empty rows
        if not row or len(row) == 0:
            return None

        name = row[0].strip() if len(row) > 0 else ""
        tickets_str = row[1].strip() if len(row) > 1 else ""

        # Warn on missing name or ticket count
        if not name:
            logger.warning("Row %d: Missing name, skipping", row_num)
            return None

        if not tickets_str:
            logger.warning("Row %d: Missing ticket count for '%s', skipping", row_num, name)
            return None

        # Raise error for non-numeric ticket counts
        try:
            tickets = int(tickets_str)
        except ValueError:
            raise ValueError(
                f"Row {row_num}: Invalid ticket count '{tickets_str}' for '{name}'. "
                "Ticket count must be a number."
            )

        if tickets <= 0:
            logger.warning("Row %d: '%s' has %d tickets, skipping", row_num, name, tickets)
            return None

        return Participant(name=name, tickets=tickets)

    def _get_participants(self) -> list[Participant]:
        result = (
            self.sheet.values()
            .get(spreadsheetId=self.spreadsheet_id, range=NAMES_TICKETS_RANGE)
            .execute()
        )
        raw_values = result.get("values", [])

        participants = []
        for i, row in enumerate(raw_values):
            row_num = i + 2  # Data starts at row 2
            participant = self._validate_participant(row, row_num)
            if participant:
                participants.append(participant)

        return participants

    def _total_tickets(self, participants: list[Participant]) -> int:
        return sum(p.tickets for p in participants)

    def _create_row_definition(self, participants: list[Participant]) -> str:
        total_count = self._total_tickets(participants)
        return f"D2:D{total_count + 1}"

    def _create_entries(self, participants: list[Participant]) -> list[list[str]]:
        entries = []
        for participant in participants:
            for _ in range(participant.tickets):
                entries.append([participant.name])

        random.shuffle(entries)
        return entries

    def _write_entries(self, row_def: str, entries: list[list[str]]) -> None:
        self.sheet.values().update(
            spreadsheetId=self.spreadsheet_id,
            range=row_def,
            body={"values": entries},
            valueInputOption="RAW"
        ).execute()

    def _select_winner(self, participants: list[Participant]) -> str:
        winning_row = random.randint(2, self._total_tickets(participants) + 1)
        winning_range = f"D{winning_row}"

        result = (
            self.sheet.values()
            .get(spreadsheetId=self.spreadsheet_id, range=winning_range)
            .execute()
        )

        winner = result.get("values", [])
        return winner[0][0] if winner else "Unknown"

    def _select_winner_from_entries(self, entries: list[list[str]]) -> str:
        """Select a winner from the entries list without reading from the sheet."""
        if not entries:
            return "Unknown"
        return random.choice(entries)[0]

    def run(self, dry_run: bool = False) -> str | None:
        """Run the raffle using participant data from a Google Sheet.

        Args:
            dry_run: If True, select winner without writing entries to the sheet.

        Returns:
            The winner's name on success, or None if no participants found.
        """
        try:
            participants = self._get_participants()

            if not participants:
                logger.warning("No participants found.")
                return None

            total = self._total_tickets(participants)
            logger.info("Loaded %d participants with %d total tickets.", len(participants), total)

            entries = self._create_entries(participants)

            if dry_run:
                logger.info("Dry run mode - not writing entries to sheet")
                winner = self._select_winner_from_entries(entries)
            else:
                row_def = self._create_row_definition(participants)
                self._write_entries(row_def, entries)
                winner = self._select_winner(participants)

            logger.info("Winner is: %s!", winner)
            return winner
        except HttpError as err:
            raise SpreadsheetError(f"Google Sheets API error: {err}") from err
