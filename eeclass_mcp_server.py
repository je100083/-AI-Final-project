import json
import os.path
import re
from fastmcp import FastMCP
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime

SCOPES = [
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/gmail.readonly'
]

mcp_server = FastMCP("EEClass_Task_Master_G14")

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
            print(f"\n1. 請授權此網址: \n{auth_url}")
            code = input("\n2. 請輸入驗證碼: ").strip()
            flow.fetch_token(code=code)
            creds = flow.credentials
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build(api_name, version, credentials=creds)

@mcp_server.tool()
async def get_eeclass_assignments() -> str:
    """
    Fetch assignments and submission status from Gmail. 
    Supports [作業] and [作業繳交] formats. 
    Fetches more history for better demo performance.
    """
    try:
        service = get_service('gmail', 'v1')
        query = "from:eeclass@my.nthu.edu.tw"
        # 抓取50封
        results = service.users().messages().list(userId='me', q=query, maxResults=50).execute()
        messages = results.get('messages', [])
        
        extracted_tasks = []
        submitted_tasks = set() # 用來記錄已繳交的作業名稱

        # 第一輪：先找出所有已繳交的作業
        for msg in messages:
            m_data = service.users().messages().get(userId='me', id=msg['id']).execute()
            subject = next(h['value'] for h in m_data['payload']['headers'] if h['name'] == 'Subject')
            if "[作業繳交]" in subject:
                task_name = re.search(r"\((.*?)\)", subject)
                if task_name:
                    submitted_tasks.add(task_name.group(1).strip())

        # 第二輪：提取待辦作業
        for msg in messages:
            m_data = service.users().messages().get(userId='me', id=msg['id']).execute()
            subject = next(h['value'] for h in m_data['payload']['headers'] if h['name'] == 'Subject')
            snippet = m_data.get('snippet', '')

            if "[作業]" in subject and "[作業繳交]" not in subject:
                course = re.search(r"課程名稱[:：]\s*(.*?)(?:\s{2}|-|\n|$)", snippet)
                task = re.search(r"作業名稱[:：]\s*(.*?)(?:\s{2}|-|\n|$)", snippet)
                deadline = re.search(r"(最後期限|繳交期限)[:：]\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", snippet)
                
                t_name = task.group(1).strip() if task else "Unknown Task"
                
                is_done = any(sub_task in t_name for sub_task in submitted_tasks)
                extracted_tasks.append({
                    "course": course.group(1).strip() if course else "Unknown Course",
                    "task": t_name,
                    "deadline": deadline.group(2) if deadline else "No Deadline",
                    "status": "Completed" if is_done else "Pending"
                })
        
        return json.dumps(extracted_tasks, ensure_ascii=False)
    except Exception as e:
        return f"Error: {e}"

@mcp_server.tool()
async def create_eeclass_task(title: str, due_date: str, notes: str) -> str:
    """
    建立 Google Task 前會先檢查是否已有相同標題的任務，避免重複。
    """
    try:
        service = get_service('tasks', 'v1')
        full_title = f"EEClass: {title}"
        
        # 抓取目前清單中的任務 (預設抓取前 100 筆)
        results = service.tasks().list(tasklist='@default', showCompleted=False).execute()
        existing_tasks = results.get('items', [])
        
        # 檢查是否有標題完全相同的任務
        for task in existing_tasks:
            if task.get('title') == full_title:
                return f"Skipped: 任務 '{full_title}' 已經在你的清單中了。"
        # -----------------------

        # 轉換日期格式
        dt = datetime.strptime(due_date, "%Y-%m-%d %H:%M")
        rfc_date = dt.strftime("%Y-%m-%dT%H:%M:00.000Z")

        task_body = {
            'title': full_title,
            'notes': notes,
            'due': rfc_date
        }
        
        result = service.tasks().insert(tasklist='@default', body=task_body).execute()
        return f"Success: 成功建立任務。 ID: {result.get('id')}"
    except Exception as e:
        return f"Error creating task: {str(e)}"

if __name__ == "__main__":
    mcp_server.run()