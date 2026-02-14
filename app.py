import logging
import os

from fastapi import FastAPI, HTTPException
from google.auth import default
from google.oauth2 import service_account

from raffle import CredentialsError, Raffle, RaffleError, SCOPES, SpreadsheetError

logger = logging.getLogger(__name__)

app = FastAPI(title="RaffleWinner API")


def _load_credentials():
    """Load Google credentials for headless operation.

    Checks SERVICE_ACCOUNT_FILE env var first, then falls back to
    Application Default Credentials (Workload Identity on Cloud Run).
    """
    sa_file = os.environ.get("SERVICE_ACCOUNT_FILE")
    if sa_file:
        return service_account.Credentials.from_service_account_file(
            sa_file, scopes=SCOPES
        )
    creds, _ = default(scopes=SCOPES)
    return creds


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/raffle/{spreadsheet_id}")
def run_raffle(spreadsheet_id: str, dry_run: bool = False):
    try:
        creds = _load_credentials()
        raffle = Raffle(spreadsheet_id, credentials=creds)
        winner = raffle.run(dry_run=dry_run)
    except SpreadsheetError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except CredentialsError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except RaffleError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if winner is None:
        raise HTTPException(status_code=404, detail="No participants found")

    return {"winner": winner}
