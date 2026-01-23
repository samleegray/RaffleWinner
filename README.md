# RaffleWinner

A Python application that runs a lottery/raffle system using Google Sheets as the data source. It reads participant names and ticket counts from a spreadsheet, creates a weighted random selection based on ticket counts, and picks a winner.

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up Google Sheets API credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - Create a new project or select an existing one
   - Enable the Google Sheets API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download the credentials and save as `credentials.json` in the project root

## Spreadsheet Setup

Create a Google Sheet with the following structure:

| Column A | Column B |
|----------|----------|
| Name     | Tickets  |
| Alice    | 5        |
| Bob      | 3        |
| Charlie  | 2        |

- Column A: Participant names (starting from row 2)
- Column B: Number of tickets/entries for each participant

The spreadsheet ID can be found in the URL:
```
https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit
```

## Usage

```bash
python main.py <SPREADSHEET_ID>
```

### CLI Options

| Flag | Description |
|------|-------------|
| `-v`, `--verbose` | Enable debug logging |
| `--dry-run` | Select winner without writing entries to the sheet |

### Examples

```bash
# Basic usage
python main.py 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms

# With verbose output
python main.py 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms --verbose

# Dry run (no writes to sheet)
python main.py 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms --dry-run
```

## How It Works

1. Reads participant data from columns A and B (name, ticket count)
2. Validates each row and converts to Participant objects
3. Expands entries based on ticket count (3 tickets = 3 entries)
4. Shuffles entries and writes to column D
5. Randomly selects a winner from column D

## Testing

Run the test suite:

```bash
python -m pytest test_raffle.py -v
# or
python -m unittest test_raffle -v
```

## Project Structure

```
RaffleWinner/
├── main.py           # CLI entry point
├── raffle.py         # Core Raffle class and business logic
├── test_raffle.py    # Unit tests
├── requirements.txt  # Python dependencies
├── credentials.json  # Google OAuth credentials (not tracked)
└── token.json        # Auto-generated auth token (not tracked)
```

## License

MIT
