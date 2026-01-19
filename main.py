import os.path
import random

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = "1IjEDMsHl39oaRAv0RhE_EJ2Itc9ExKKG85NgNRXpe6Y"
# SAMPLE_RANGE_NAME = "Class Data!A2:E"
SAMPLE_RANGE_NAME = "A1:B"

def main():
  """Shows basic usage of the Sheets API.
  Prints values from a sample spreadsheet.
  """
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

  try:
    service = build("sheets", "v4", credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = (
        sheet.values()
        .get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=SAMPLE_RANGE_NAME)
        .execute()
    )
    values = result.get("values", [])

    if not values:
      print("No data found.")
      return

    print(values)
    row_def = create_row_definition(values)
    name_array = create_name_array(values)

    winning_row = random.randint(0, total_tickets(values))
    print(f"Winning is row #: {winning_row}")

    winning_range = "D" + str(winning_row)
    result = (
      sheet.values()
      .get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=winning_range)
      .execute()
    )
    print(f"Winner is: {result.get("values", [])}!")

    result = (sheet.values().update(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                   range=row_def,
                                   body={"values": name_array},
                                   valueInputOption="RAW")
              .execute())
    print(result)
  except HttpError as err:
    print(err)


def total_tickets(ticket_stats):
  total_count = 0

  for stat in ticket_stats:
    print(f"{stat[0]} bought {stat[1]} tickets.")
    total_count += int(stat[1])

  return total_count

def create_row_definition(ticket_stats):
  row_definition = "D1:D"
  total_count = total_tickets(ticket_stats)

  row_definition += str(total_count)
  print(row_definition)
  return row_definition


def create_name_array(ticket_stats):
  array = []
  for stat in ticket_stats:
    player_name = stat[0]
    ticket_count = int(stat[1])
    for i in range(ticket_count):
      array.append([player_name])

  random.shuffle(array)
  print(array)
  return array

if __name__ == "__main__":
  main()