import asyncio
from autogen import AssistantAgent, UserProxyAgent
from autogen.mcp import create_toolkit
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 1. 定義大腦模型 (假設你使用本地端 Ollama 執行 phi4-mini-instruct)
llm_config = {
    "config_list": [
        {
            "model": "qwen2.5:32b", #qwen2.5:7b
            "base_url": "http://localhost:11434/v1", 
            "api_key": "ollama"
        }
    ],
    "temperature": 0.8,
    "cache_seed": None 
}

# 2. 建立分析助理 (大腦)
analyst = AssistantAgent(
    name="EEClass_Analyst",
    system_message=
    """
    你是一個 eeclass 學習助理。
    【重要任務】：
    1. 呼叫 get_eeclass_assignments 獲取最近 50 封郵件的資訊。
    2. 根據回傳的 JSON，區分「Pending (待處理)」與「Completed (已完成)」的作業。
    3. 對於「Completed」的作業，請給予使用者熱情的鼓勵（例如：做得好！）。
    4. 對於「Pending」的作業：
       - 列出截止日期。
       - 進行 1-10 分的難度評估。
       - 詢問使用者是否要將其加入「Google Tasks (任務清單)」。
    5. 若使用者同意，呼叫 create_eeclass_task。
    """,
    llm_config=llm_config
)

# 3. 建立使用者代理 (負責執行工具與確認)
user_proxy = UserProxyAgent(
    name="Student_User",
    human_input_mode="ALWAYS",
    code_execution_config=False,
)

# 4. 串接 MCP Server 並註冊工具
async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["eeclass_mcp_server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            toolkit = await create_toolkit(session=session)
            toolkit.register_for_llm(analyst)
            toolkit.register_for_execution(user_proxy)
            
            # 5. 開始對話測試
            await user_proxy.a_initiate_chat(
                analyst,
                message="請幫我檢查最新的 eeclass 信件，並告訴我有哪些作業需要排程？"
            )

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n使用者中斷程式執行")
