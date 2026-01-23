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

## Dependencies

- `google-auth-oauthlib` - OAuth2 authentication flow
- `google-auth-httplib2` - HTTP transport for Google Auth
- `google-api-python-client` - Google Sheets API client

## Setup Requirements

- **credentials.json**: Google OAuth credentials file (required, gitignored)
- **token.json**: Auto-generated after first OAuth authentication (gitignored)

If modifying the Google API scopes in `SCOPES`, delete `token.json` to force re-authentication.

## Architecture

The application uses the Google Sheets API v4. All code is in `main.py`, organized as a `Raffle` class.

### Raffle Class

The `Raffle` class encapsulates all spreadsheet operations and state.

**Constructor:**
- `Raffle(spreadsheet_id: str)` - Initialize with a Google Spreadsheet ID

**Public Methods:**
- `run()` - Execute the raffle workflow

**Properties:**
- `sheet` - Lazily initialized Google Sheets resource (authenticates on first access)

**Private Methods:**

| Method | Purpose |
|--------|---------|
| `_authorize()` | Handles OAuth2 authentication with token caching |
| `_build_service()` | Builds the Google Sheets API service |
| `_authorize_and_build()` | Combines auth and service creation |
| `_get_participants()` | Reads names and ticket counts from columns A2:B |
| `_total_tickets()` | Calculates total ticket count from all participants |
| `_create_row_definition()` | Generates the D column range (e.g., "D2:D50") |
| `_create_entries()` | Expands names by ticket count and shuffles |
| `_write_entries()` | Writes shuffled entries to column D |
| `_select_winner()` | Randomly selects a row from column D |

### Data Flow

1. Read participant data from columns A:B (name, ticket count)
2. Expand entries (3 tickets = 3 entries for that name)
3. Shuffle and write to column D
4. Randomly select a row from D as the winner
