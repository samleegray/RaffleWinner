import unittest
from unittest.mock import MagicMock, patch

from raffle import (
    CredentialsError,
    Participant,
    Raffle,
    SpreadsheetError,
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

        with patch.object(self.raffle, "_write_entries") as mock_write:
            result = self.raffle.run(dry_run=True)

        mock_write.assert_not_called()
        self.assertEqual(result, "Alice")

    @patch.object(Raffle, "_select_winner")
    @patch.object(Raffle, "_write_entries")
    @patch.object(Raffle, "_get_participants")
    def test_run_returns_winner(self, mock_get, mock_write, mock_select):
        mock_get.return_value = [
            Participant(name="Alice", tickets=2),
            Participant(name="Bob", tickets=1),
        ]
        mock_select.return_value = "Bob"

        result = self.raffle.run(dry_run=False)

        self.assertEqual(result, "Bob")
        mock_write.assert_called_once()


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


if __name__ == "__main__":
    unittest.main()
