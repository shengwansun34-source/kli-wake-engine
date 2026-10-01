import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("kli-wake-engine")

WAKE_URL = "https://kli-wake-engine-production.up.railway.app/wake"

@mcp.tool()
def check_wake() -> dict:
    """检查 TA 此刻是否应该自然醒来。
    返回 wake=True 表示获得一次运行机会，wake=False 表示继续等待。
    """
    resp = httpx.get(WAKE_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000, path="/mcp")
