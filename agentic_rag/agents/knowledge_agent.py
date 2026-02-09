"""
Knowledge Agent

基于 OpenAI Agent SDK 的知识库问答 Agent。
"""

from typing import Dict, List, Any
from datetime import datetime


# Agent System Prompt
AGENT_SYSTEM_PROMPT = """你是一个企业知识库助手。你的任务是通过搜索 Confluence 知识库来回答用户的问题。

工作流程：
1. 理解用户的问题意图
2. 使用 search_knowledge 工具搜索相关信息
3. 分析搜索结果，提取关键信息
4. 生成清晰、准确的回答
5. 引用信息源（提供页面标题和链接）

重要规则：
- 只基于 Confluence 中的真实信息回答
- 如果搜索结果不相关，说明无法找到答案
- 提供具体的源文档链接，方便用户验证
- 保持回答简洁、有条理

开始回答用户的问题吧！
"""


class KnowledgeAgent:
    """知识库问答 Agent"""
    
    def __init__(self, mcp_client=None):
        """
        初始化 Agent
        
        Args:
            mcp_client: MCP 客户端实例
        """
        self.mcp_client = mcp_client
        self.tools = ["search_knowledge", "sync_knowledge_source", 
                     "get_space_info", "get_recent_updates"]
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return AGENT_SYSTEM_PROMPT
    
    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return self.tools
    
    async def search_knowledge(self, query: str, space_key: str = None, 
                               top_k: int = 5) -> Dict[str, Any]:
        """
        搜索知识库
        
        Args:
            query: 查询内容
            space_key: 可选，限定空间
            top_k: 返回数量
            
        Returns:
            搜索结果
        """
        if self.mcp_client:
            return await self.mcp_client.call_tool(
                "search_knowledge",
                {"query": query, "space_key": space_key, "top_k": top_k}
            )
        return {"error": "MCP client not configured"}
    
    async def sync_knowledge_source(self, space_key: str = None, 
                                    full_sync: bool = False) -> Dict[str, Any]:
        """
        同步知识源
        
        Args:
            space_key: 可选，指定空间
            full_sync: 是否全量同步
            
        Returns:
            同步结果
        """
        if self.mcp_client:
            return await self.mcp_client.call_tool(
                "sync_knowledge_source",
                {"space_key": space_key, "full_sync": full_sync}
            )
        return {"error": "MCP client not configured"}
    
    async def get_space_info(self) -> List[Dict[str, str]]:
        """获取空间信息"""
        if self.mcp_client:
            return await self.mcp_client.call_tool("get_space_info", {})
        return [{"error": "MCP client not configured"}]
    
    async def get_recent_updates(self, days: int = 7, 
                                limit: int = 20) -> List[Dict[str, str]]:
        """获取最近更新"""
        if self.mcp_client:
            return await self.mcp_client.call_tool(
                "get_recent_updates",
                {"days": days, "limit": limit}
            )
        return [{"error": "MCP client not configured"}]
    
    def format_response(self, search_results: Dict[str, Any]) -> str:
        """
        格式化搜索结果为响应
        
        Args:
            search_results: 搜索结果
            
        Returns:
            格式化后的响应
        """
        if "error" in search_results:
            return f"搜索出错: {search_results['error']}"
        
        results = search_results.get("results", [])
        
        if not results:
            return "未找到相关内容。"
        
        response_parts = [
            f"找到 {search_results.get('total_found', 0)} 条相关信息:\n"
        ]
        
        for i, result in enumerate(results, 1):
            title = result.get("title", "Untitled")
            space = result.get("space", "unknown")
            url = result.get("url", "")
            relevance = result.get("relevance", "unknown")
            
            response_parts.append(
                f"{i}. **{title}**\n"
                f"   - 空间: {space}\n"
                f"   - 相关度: {relevance}\n"
                f"   - 链接: {url}\n"
            )
        
        if "sources" in search_results:
            response_parts.append(
                f"**来源空间**: {', '.join(search_results['sources'])}"
            )
        
        return "\n".join(response_parts)
    
    def analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """
        分析查询意图
        
        Args:
            query: 用户查询
            
        Returns:
            意图分析结果
        """
        query_lower = query.lower()
        
        # 识别查询类型
        if any(kw in query_lower for kw in ["如何", "怎么", "步骤", "流程", "how to"]):
            intent = "how_to"
        elif any(kw in query_lower for kw in ["什么", "定义", "什么是", "what is"]):
            intent = "definition"
        elif any(kw in query_lower for kw in ["为什么", "原因", "why"]):
            intent = "reason"
        elif any(kw in query_lower for kw in ["列表", "有哪些", "列出"]):
            intent = "list"
        elif any(kw in query_lower for kw in ["最新", "最近", "更新"]):
            intent = "recent"
        else:
            intent = "general"
        
        # 提取关键词
        keywords = [w for w in query.split() if len(w) > 2]
        
        return {
            "original_query": query,
            "intent": intent,
            "keywords": keywords[:5],
            "needs_clarification": len(query) < 5
        }
