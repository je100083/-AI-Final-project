from eeclass_mcp_server import get_service
import json

def test_everything():
    print("--- 測試 1：抓取 50 封信件並判斷狀態 ---")
    # 測試抓取 (會測試到你新的 [作業繳交] 邏輯)
    gmail_service = get_service('gmail', 'v1')
    # 這裡直接呼叫你寫在 server 裡的邏輯
    from eeclass_mcp_server import get_eeclass_assignments
    import asyncio
    res = asyncio.run(get_eeclass_assignments())
    print(f"結果：{res}")

    print("\n--- 測試 2：建立測試任務 ---")
    tasks_service = get_service('tasks', 'v1')
    from eeclass_mcp_server import create_eeclass_task
    # 建立一個明天截止的測試任務
    task_res = asyncio.run(create_eeclass_task(
        title="Demo測試作業", 
        due_date="2026-05-11 23:59", 
        notes="這是從 MCP 測試腳本建立的"
    ))
    print(task_res)

if __name__ == "__main__":
    test_everything()