import unittest
from unittest.mock import MagicMock, patch

from google.auth.exceptions import RefreshError

from raffle import (
    CredentialsError,
    DATE_COLUMN,
    Participant,
    Raffle,
    SpreadsheetError,
    WINNER_COLUMN,
)


class TestParticipantDataclass(unittest.TestCase):
    def test_participant_creation(self):
        p = Participant(name="Alice", tickets=5)
        self.assertEqual(p.name, "Alice")
        self.assertEqual(p.tickets, 5)

    def test_participant_equality(self):
        p1 = Participant(name="Bob", tickets=3)
        p2 = Participant(name="Bob", tickets=3)
        self.assertEqual(p1, p2)


class TestSpreadsheetIdValidation(unittest.TestCase):
    def test_valid_spreadsheet_id(self):
        valid_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        raffle = Raffle(valid_id)
        self.assertEqual(raffle.spreadsheet_id, valid_id)

    def test_invalid_spreadsheet_id_too_short(self):
        with self.assertRaises(SpreadsheetError) as ctx:
            Raffle("abc123")
        self.assertIn("Invalid spreadsheet ID format", str(ctx.exception))

    def test_invalid_spreadsheet_id_invalid_chars(self):
        with self.assertRaises(SpreadsheetError) as ctx:
            Raffle("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2up!s")
        self.assertIn("Invalid spreadsheet ID format", str(ctx.exception))


class TestValidateParticipant(unittest.TestCase):
    def setUp(self):
        with patch.object(Raffle, "_validate_spreadsheet_id"):
            self.raffle = Raffle("test_id")

    def test_valid_participant(self):
        result = self.raffle._validate_participant(["Alice", "5"], 2)
        self.assertEqual(result, Participant(name="Alice", tickets=5))

    def test_empty_row(self):
        result = self.raffle._validate_participant([], 2)
        self.assertIsNone(result)

    def test_missing_name(self):
        result = self.raffle._validate_participant(["", "5"], 2)
        self.assertIsNone(result)

    def test_missing_tickets(self):
        result = self.raffle._validate_participant(["Alice", ""], 2)
        self.assertIsNone(result)

    def test_invalid_tickets_non_numeric(self):
        with self.assertRaises(ValueError) as ctx:
            self.raffle._validate_participant(["Alice", "five"], 2)
        self.assertIn("Invalid ticket count", str(ctx.exception))

    def test_zero_tickets(self):
        result = self.raffle._validate_participant(["Alice", "0"], 2)
        self.assertIsNone(result)

    def test_negative_tickets(self):
        result = self.raffle._validate_participant(["Alice", "-1"], 2)
        self.assertIsNone(result)

    def test_whitespace_trimmed(self):
        result = self.raffle._validate_participant(["  Alice  ", "  5  "], 2)
        self.assertEqual(result, Participant(name="Alice", tickets=5))


class TestTotalTickets(unittest.TestCase):
    def setUp(self):
        with patch.object(Raffle, "_validate_spreadsheet_id"):
            self.raffle = Raffle("test_id")

    def test_total_tickets(self):
        participants = [
            Participant(name="Alice", tickets=5),
            Participant(name="Bob", tickets=3),
            Participant(name="Charlie", tickets=2),
        ]
        self.assertEqual(self.raffle._total_tickets(participants), 10)

    def test_total_tickets_empty(self):
        self.assertEqual(self.raffle._total_tickets([]), 0)

    def test_total_tickets_single(self):
        participants = [Participant(name="Alice", tickets=7)]
        self.assertEqual(self.raffle._total_tickets(participants), 7)


class TestCreateEntries(unittest.TestCase):
    def setUp(self):
        with patch.object(Raffle, "_validate_spreadsheet_id"):
            self.raffle = Raffle("test_id")

    def test_create_entries_expansion(self):
        participants = [
            Participant(name="Alice", tickets=2),
            Participant(name="Bob", tickets=1),
        ]
        entries = self.raffle._create_entries(participants)

        # Should have 3 total entries
        self.assertEqual(len(entries), 3)

        # Should contain correct names
        names = [e[0] for e in entries]
        self.assertEqual(names.count("Alice"), 2)
        self.assertEqual(names.count("Bob"), 1)

    def test_create_entries_shuffled(self):
        participants = [
            Participant(name="Alice", tickets=10),
            Participant(name="Bob", tickets=10),
        ]
        # Run multiple times to check shuffling happens
        results = set()
        for _ in range(10):
            entries = self.raffle._create_entries(participants)
            results.add(tuple(e[0] for e in entries))

        # Should have different orderings (very unlikely to be same 10 times)
        self.assertGreater(len(results), 1)


class TestCredentialsError(unittest.TestCase):
    def test_missing_credentials_file(self):
        valid_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        raffle = Raffle(valid_id)

        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = False
            with self.assertRaises(CredentialsError) as ctx:
                raffle._authorize()
            self.assertIn("credentials.json not found", str(ctx.exception))

    @patch("raffle.InstalledAppFlow")
    @patch("raffle.Credentials")
    @patch("os.path.exists")
    @patch("os.remove")
    def test_refresh_error_removes_token_and_reauthorizes(
        self, mock_remove, mock_exists, mock_creds_class, mock_flow_class
    ):
        valid_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        raffle = Raffle(valid_id)

        # Setup: token.json exists, credentials.json exists
        mock_exists.side_effect = lambda f: f in ["token.json", "credentials.json"]

        # Setup: expired credentials that fail to refresh
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "some_token"
        mock_creds.refresh.side_effect = RefreshError("Token has been expired or revoked.")
        mock_creds_class.from_authorized_user_file.return_value = mock_creds

        # Setup: OAuth flow returns new credentials
        mock_new_creds = MagicMock()
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_new_creds
        mock_flow_class.from_client_secrets_file.return_value = mock_flow

        with patch("builtins.open", MagicMock()):
            result = raffle._authorize()

        # Verify token.json was removed
        mock_remove.assert_called_once_with("token.json")
        # Verify new OAuth flow was started
        mock_flow_class.from_client_secrets_file.assert_called_once()
        # Verify new credentials are returned
        self.assertEqual(result, mock_new_creds)


class TestRunMethod(unittest.TestCase):
    def setUp(self):
        with patch.object(Raffle, "_validate_spreadsheet_id"):
            self.raffle = Raffle("test_id")

    @patch.object(Raffle, "_get_participants")
    def test_run_no_participants(self, mock_get):
        mock_get.return_value = []
        result = self.raffle.run()
        self.assertIsNone(result)

    @patch.object(Raffle, "_select_winner_from_entries")
    @patch.object(Raffle, "_get_participants")
    def test_run_dry_run_does_not_write(self, mock_get, mock_select):
        mock_get.return_value = [Participant(name="Alice", tickets=1)]
        mock_select.return_value = "Alice"

        with patch.object(self.raffle, "_write_entries") as mock_write, \
             patch.object(self.raffle, "_write_winner_record") as mock_record:
            result = self.raffle.run(dry_run=True)

        mock_write.assert_not_called()
        mock_record.assert_not_called()
        self.assertEqual(result, "Alice")

    @patch.object(Raffle, "_write_winner_record")
    @patch.object(Raffle, "_select_winner")
    @patch.object(Raffle, "_write_entries")
    @patch.object(Raffle, "_get_participants")
    def test_run_returns_winner(self, mock_get, mock_write, mock_select, mock_record):
        mock_get.return_value = [
            Participant(name="Alice", tickets=2),
            Participant(name="Bob", tickets=1),
        ]
        mock_select.return_value = "Bob"

        result = self.raffle.run(dry_run=False)

        self.assertEqual(result, "Bob")
        mock_write.assert_called_once()
        mock_record.assert_called_once_with("Bob")


class TestSelectWinnerFromEntries(unittest.TestCase):
    def setUp(self):
        with patch.object(Raffle, "_validate_spreadsheet_id"):
            self.raffle = Raffle("test_id")

    def test_select_from_empty_entries(self):
        result = self.raffle._select_winner_from_entries([])
        self.assertEqual(result, "Unknown")

    def test_select_returns_valid_entry(self):
        entries = [["Alice"], ["Bob"], ["Charlie"]]
        result = self.raffle._select_winner_from_entries(entries)
        self.assertIn(result, ["Alice", "Bob", "Charlie"])


class TestGetFirstEmptyRow(unittest.TestCase):
    def setUp(self):
        with patch.object(Raffle, "_validate_spreadsheet_id"):
            self.raffle = Raffle("test_id")
        self.mock_sheet = MagicMock()
        self.raffle._sheet = self.mock_sheet

    def test_empty_column_returns_start_row(self):
        self.mock_sheet.values().get().execute.return_value = {"values": []}
        result = self.raffle._get_first_empty_row("A")
        self.assertEqual(result, 1)

    def test_finds_first_empty_in_middle(self):
        self.mock_sheet.values().get().execute.return_value = {
            "values": [["data"], ["data"], [], ["data"]]
        }
        result = self.raffle._get_first_empty_row("A")
        self.assertEqual(result, 3)

    def test_finds_empty_string_row(self):
        self.mock_sheet.values().get().execute.return_value = {
            "values": [["data"], ["  "], ["data"]]
        }
        result = self.raffle._get_first_empty_row("A")
        self.assertEqual(result, 2)

    def test_all_filled_returns_next_row(self):
        self.mock_sheet.values().get().execute.return_value = {
            "values": [["a"], ["b"], ["c"]]
        }
        result = self.raffle._get_first_empty_row("A")
        self.assertEqual(result, 4)

    def test_custom_start_row(self):
        self.mock_sheet.values().get().execute.return_value = {
            "values": [["data"], ["data"]]
        }
        result = self.raffle._get_first_empty_row("A", start_row=5)
        self.assertEqual(result, 7)

    def test_uses_correct_range_notation(self):
        self.mock_sheet.values().get().execute.return_value = {"values": []}
        self.raffle._get_first_empty_row("F", start_row=2)
        self.mock_sheet.values().get.assert_called()
        call_kwargs = self.mock_sheet.values().get.call_args[1]
        self.assertEqual(call_kwargs["range"], "F2:F")


class TestWriteWinnerRecord(unittest.TestCase):
    def setUp(self):
        with patch.object(Raffle, "_validate_spreadsheet_id"):
            self.raffle = Raffle("test_id")
        self.mock_sheet = MagicMock()
        self.raffle._sheet = self.mock_sheet

    @patch("raffle.date")
    def test_writes_date_and_winner(self, mock_date):
        mock_date.today.return_value.strftime.return_value = "01/30/2026"
        self.mock_sheet.values().get().execute.return_value = {"values": [["header"]]}

        self.raffle._write_winner_record("Alice")

        # Verify two update calls were made
        self.assertEqual(self.mock_sheet.values().update.call_count, 2)

    @patch("raffle.date")
    def test_writes_correct_date_format(self, mock_date):
        mock_date.today.return_value.strftime.return_value = "01/30/2026"
        self.mock_sheet.values().get().execute.return_value = {"values": []}

        self.raffle._write_winner_record("Alice")

        # Check strftime was called with correct format
        mock_date.today().strftime.assert_called_with("%m/%d/%Y")

    @patch("raffle.date")
    def test_writes_winner_with_at_prefix(self, mock_date):
        mock_date.today.return_value.strftime.return_value = "01/30/2026"
        self.mock_sheet.values().get().execute.return_value = {"values": []}

        self.raffle._write_winner_record("Alice")

        # Find the call that writes to winner column
        calls = self.mock_sheet.values().update.call_args_list
        winner_call = [c for c in calls if WINNER_COLUMN in str(c)]
        self.assertTrue(len(winner_call) > 0)

    @patch.object(Raffle, "_get_first_empty_row")
    @patch("raffle.date")
    def test_writes_to_correct_rows(self, mock_date, mock_get_empty):
        mock_date.today.return_value.strftime.return_value = "01/30/2026"
        mock_get_empty.side_effect = [5, 5]  # Date row, Winner row

        self.raffle._write_winner_record("Bob")

        calls = self.mock_sheet.values().update.call_args_list
        ranges_used = [c[1]["range"] for c in calls]
        self.assertIn(f"{DATE_COLUMN}5", ranges_used)
        self.assertIn(f"{WINNER_COLUMN}5", ranges_used)


if __name__ == "__main__":
    unittest.main()
