from datetime import datetime, timezone, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os.path

SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_FILE = 'token.json'
CREDS_FILE = 'credentials.json'

def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def add_event(title, start_time_str, duration_hours=1):
    service = get_calendar_service()
    start = datetime.fromisoformat(start_time_str)
    end = start + timedelta(hours=duration_hours)

    event = {
        'summary': title,
        'start': {'dateTime': start.isoformat(), 'timeZone': 'Asia/Seoul'},
        'end': {'dateTime': end.isoformat(), 'timeZone': 'Asia/Seoul'}
    }

    service.events().insert(calendarId='primary', body=event).execute()
    print(f"[✓] '{title}' 일정이 등록되었습니다.")

def find_event(service, title, start_time_str):
    start = datetime.fromisoformat(start_time_str).astimezone(timezone.utc)
    end = start + timedelta(hours=1)

    events_result = service.events().list(
        calendarId='primary',
        timeMin=start.isoformat(),  # ISO + Z 포함
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    for event in events_result.get('items', []):
        if event.get('summary') == title:
            return event
    return None

def delete_event(title, start_time_str):
    service = get_calendar_service()
    event = find_event(service, title, start_time_str)
    if not event:
        print("[X] 삭제할 일정을 찾을 수 없습니다.")
        return
    service.events().delete(calendarId='primary', eventId=event['id']).execute()
    print(f"[✓] '{title}' 일정이 삭제되었습니다.")

def update_event(title, old_time_str, new_time_str):
    service = get_calendar_service()
    event = find_event(service, title, old_time_str)
    if not event:
        print("[X] 수정할 일정을 찾을 수 없습니다.")
        return

    new_start = datetime.fromisoformat(new_time_str)
    new_end = new_start + timedelta(hours=1)
    event['start']['dateTime'] = new_start.isoformat()
    event['end']['dateTime'] = new_end.isoformat()

    service.events().update(calendarId='primary', eventId=event['id'], body=event).execute()
    print(f"[✓] '{title}' 일정이 수정되었습니다.")

# ========== 테스트 예제 ==========
if __name__ == '__main__':
    # 예제 1: 일정 추가
    add_event("지나랑 점심", "2025-08-05T12:00:00")

    # 예제 2: 일정 수정
    update_event("지나랑 점심", "2025-08-05T12:00:00", "2025-08-05T13:00:00")

    # 예제 3: 일정 삭제
    delete_event("지나랑 점심", "2025-08-05T13:00:00")
