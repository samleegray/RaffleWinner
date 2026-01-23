# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RaffleWinner is a Python application that runs a lottery/raffle system using Google Sheets as the data source. It reads participant names and ticket counts from a spreadsheet, creates a weighted random selection based on ticket counts, and picks a winner.

## Running the Application

```bash
python main.py
```

## Setup Requirements

- **credentials.json**: Google OAuth credentials file (required, gitignored)
- **token.json**: Auto-generated after first OAuth authentication

If modifying the Google API scopes in `SCOPES`, delete `token.json` to force re-authentication.

## Architecture

The application uses the Google Sheets API v4:

1. **Authorization flow** (`authorize()`): Handles OAuth2 authentication with token caching
2. **Data retrieval** (`get_names_and_tickets()`): Reads names and ticket counts from columns A:B
3. **Raffle setup** (`create_name_array()`, `update_random_names()`): Expands ticket counts into individual entries, shuffles them, and writes to column D
4. **Winner selection** (`get_winner()`): Randomly selects a row from column D

Data flow: Spreadsheet A:B (name, ticket count) → Shuffled entries in column D → Random row selection from D.
