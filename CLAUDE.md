# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RaffleWinner is a Python application that runs a lottery/raffle system using Google Sheets as the data source. It reads participant names and ticket counts from a spreadsheet, creates a weighted random selection based on ticket counts, and picks a winner.

## Running the Application

```bash
python main.py <SPREADSHEET_ID>
```

The spreadsheet ID can be found in the Google Sheets URL:
`https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit`

### CLI Options

| Flag | Description |
|------|-------------|
| `-v`, `--verbose` | Enable debug logging |
| `--dry-run` | Select winner without writing entries to the sheet |

Examples:
```bash
# Run with verbose output
python main.py <SPREADSHEET_ID> --verbose

# Run in dry-run mode (no writes to sheet)
python main.py <SPREADSHEET_ID> --dry-run
```

## Dependencies

Install dependencies with:
```bash
pip install -r requirements.txt
```

- `google-auth-oauthlib` - OAuth2 authentication flow
- `google-auth-httplib2` - HTTP transport for Google Auth
- `google-api-python-client` - Google Sheets API client

## Setup Requirements

- **credentials.json**: Google OAuth credentials file (required, gitignored)
- **token.json**: Auto-generated after first OAuth authentication (gitignored)

If modifying the Google API scopes in `SCOPES`, delete `token.json` to force re-authentication.

## Testing

Run tests with pytest:
```bash
python -m pytest test_raffle.py -v
```

## Architecture

The application uses the Google Sheets API v4.

### File Structure

- `main.py` - Entry point with CLI argument parsing and logging configuration
- `raffle.py` - Contains the `Raffle` class with all business logic
- `test_raffle.py` - Unit tests with mocked Google API
- `requirements.txt` - Python dependencies

### Logging

The application uses Python's `logging` module. Logging is configured in `main.py` at INFO level (DEBUG with `--verbose`). The `Raffle` class uses a module-level logger (`logging.getLogger(__name__)`).

### Data Types

**Participant Dataclass:**
```python
@dataclass
class Participant:
    name: str
    tickets: int
```

### Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `SCOPES` | `["...spreadsheets"]` | Google API permissions |
| `NAMES_TICKETS_RANGE` | `"A2:B"` | Range for participant data |
| `DATE_COLUMN` | `"F"` | Column for winner history dates |
| `WINNER_COLUMN` | `"G"` | Column for winner history names |

### Custom Exceptions

| Exception | Description |
|-----------|-------------|
| `RaffleError` | Base exception for all raffle errors |
| `CredentialsError` | Missing or invalid credentials.json |
| `SpreadsheetError` | Invalid spreadsheet ID or API access error |

### Raffle Class

The `Raffle` class encapsulates all spreadsheet operations and state.

**Constructor:**
- `Raffle(spreadsheet_id: str)` - Initialize with a Google Spreadsheet ID (validates format)

**Public Methods:**
- `run(dry_run: bool = False) -> str | None` - Execute the raffle workflow, returns winner name or None

**Properties:**
- `sheet` - Lazily initialized Google Sheets resource (authenticates on first access)

**Private Methods:**

| Method | Purpose |
|--------|---------|
| `_validate_spreadsheet_id()` | Validates spreadsheet ID format (44 chars, alphanumeric) |
| `_authorize()` | Handles OAuth2 authentication with token caching |
| `_build_service()` | Builds the Google Sheets API service |
| `_authorize_and_build()` | Combines auth and service creation |
| `_validate_participant()` | Validates and converts row to Participant |
| `_get_participants()` | Reads names and ticket counts from columns A2:B |
| `_total_tickets()` | Calculates total ticket count from all participants |
| `_get_first_empty_row()` | Finds the first empty row in a given column |
| `_create_row_definition()` | Generates the D column range (e.g., "D2:D50") |
| `_create_entries()` | Expands names by ticket count and shuffles |
| `_write_entries()` | Writes shuffled entries to column D |
| `_select_winner()` | Randomly selects a row from column D |
| `_select_winner_from_entries()` | Selects winner from entries list (for dry-run) |
| `_write_winner_record()` | Writes date and winner to history columns F and G |

### Spreadsheet Column Layout

| Column | Purpose |
|--------|---------|
| A | Participant names |
| B | Ticket counts |
| D | Expanded entries (one row per ticket) |
| F | Winner history dates (MM/DD/YYYY format) |
| G | Winner history names (prefixed with @) |

### Data Flow

1. Read participant data from columns A:B (name, ticket count)
2. Validate each row and convert to Participant objects
3. Expand entries (3 tickets = 3 entries for that name)
4. Shuffle and write to column D (skipped in dry-run mode)
5. Randomly select a row from D as the winner
6. Record the date and winner to columns F and G (skipped in dry-run mode)
