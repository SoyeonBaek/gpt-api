from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import json
from datetime import datetime, timedelta

SCOPES = ['https://www.googleapis.com/auth/calendar']

client_secret_json = "client_secret_772705558537-i205a18oj8nmv46gn73ru848j24600so.apps.googleusercontent.com.json"

def get_calendar_service():
    creds = None

    if os.path.exists('token.json'):
        with open('token.json', 'r') as token:
            creds_data = json.load(token)
            creds = Request().from_authorized_user_info(info=creds_data, scopes=SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_json, SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token_file:
            token_file.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)
def create_event():
    service = get_calendar_service()
    start_time = datetime(2025, 8, 5, 12, 0)
    end_time = start_time + timedelta(hours=1)

    event = {
        'summary': 'Lunch with my friends',
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'Asia/Seoul'
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'Asia/Seoul'
        }
    }

    event_result = service.events().insert(calendarId='primary', body=event).execute()
    print("Added :", event_result.get('htmlLink'))

if __name__ == '__main__':
    create_event()

