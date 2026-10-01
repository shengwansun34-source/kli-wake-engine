import os
import uvicorn
from mcp.server.fastmcp import FastMCP
from app import wake_check

mcp = FastMCP("kli-wake-engine")

@mcp.tool()
def check_wake() -> dict:
 """检查现在是否应该唤醒 AI。
 wake=True 表示获得一次运行机会，wake=False 表示继续等待。
 """
 return wake_check()

if __name__ == "__main__":
 port = int(os.environ.get("PORT", "8080"))
 uvicorn.run(
 mcp.streamable_http_app(),
 host="0.0.0.0",
 port=port,
 )
