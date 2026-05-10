import json
import os.path
import re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.readonly'
]

def get_service(api_name, version):
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json',
                SCOPES,
                redirect_uri='urn:ietf:wg:oauth:2.0:oob'
            )
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(f"\n1. 請在瀏覽器打開此網址並授權: \n{auth_url}")
            code = input("\n2. 請輸入授權後的『驗證碼』: ").strip()
            flow.fetch_token(code=code)
            creds = flow.credentials
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build(api_name, version, credentials=creds)


def fetch_assignments():
    service = get_service('gmail', 'v1')
    query = "from:eeclass@my.nthu.edu.tw"
    results = service.users().messages().list(userId='me', q=query, maxResults=50).execute()
    messages = results.get('messages', [])

    print(f"共找到 {len(messages)} 封 eeclass 信件，開始過濾作業...\n")

    extracted_tasks = []
    for msg in messages:
        m_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        snippet = m_data.get('snippet', '')
        subject = ""
        for header in m_data['payload']['headers']:
            if header['name'] == 'Subject':
                subject = header['value']

        print(f"[subject] {subject}")

        if "[作業]" in subject:
            course = re.search(r"課程名稱[:：]\s*(.*?)(?:\s{2}|\n|$)", snippet)
            task = re.search(r"作業名稱[:：]\s*(.*?)(?:\s{2}|\n|$)", snippet)
            deadline = re.search(r"(最後期限|繳交期限)[:：]\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", snippet)

            extracted_tasks.append({
                "type": "Assignment",
                "course": course.group(1).strip() if course else "Unknown Course",
                "task": task.group(1).strip() if task else subject,
                "deadline": deadline.group(1) if deadline else "No Deadline Found",
                "raw_info": snippet
            })

        if deadline:
            deadline_str = deadline.group(2)
            if datetime.strptime(deadline_str, "%Y-%m-%d %H:%M") < datetime.now():
                print(f"跳過已過期作業: {subject}")
                continue

    return extracted_tasks


if __name__ == "__main__":
    tasks = fetch_assignments()

    print("\n" + "="*60)
    print(f"找到 {len(tasks)} 個作業：")
    print("="*60)

    if not tasks:
        print("沒有找到任何作業。")
    else:
        for i, t in enumerate(tasks, 1):
            print(f"\n【作業 {i}】")
            print(f"  課程：{t['course']}")
            print(f"  作業：{t['task']}")
            print(f"  截止：{t['deadline']}")