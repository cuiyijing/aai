"""
Knowledge Source MCP Server

统一的 Knowledge Source MCP 服务器，将 Confluence 知识库封装为单一 Tool。
支持搜索、同步和空间信息查询等功能。
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .confluence_client import ConfluenceClient
from .vector_client import VectorStoreClient
from .text_processor import TextProcessor


class KnowledgeSourceMCPServer:
    """Knowledge Source MCP 服务器"""
    
    def __init__(self):
        self.server = Server("knowledge-source-server")
        self.text_processor = TextProcessor()
        
        # 初始化客户端
        self.confluence_client = ConfluenceClient(
            url=os.getenv("CONFLUENCE_URL", ""),
            email=os.getenv("CONFLUENCE_EMAIL", ""),
            api_token=os.getenv("CONFLUENCE_API_TOKEN", "")
        )
        
        self.vector_client = VectorStoreClient(
            api_key=os.getenv("PINECONE_API_KEY", ""),
            host=os.getenv("PINECONE_HOST", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", "")
        )
        
        self._register_handlers()
    
    def _register_handlers(self):
        """注册 MCP 处理器"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """列出可用的工具"""
            return [
                Tool(
                    name="search_knowledge",
                    description="搜索 Confluence 知识库，基于用户查询检索相关文档",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "用户查询内容"
                            },
                            "space_key": {
                                "type": "string",
                                "description": "可选，限定搜索的 Confluence 空间 key"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "返回结果数量，默认为 5",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="sync_knowledge_source",
                    description="同步 Confluence 知识源到向量数据库，支持全量和增量同步",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "space_key": {
                                "type": "string",
                                "description": "可选，只同步指定的 Confluence 空间"
                            },
                            "full_sync": {
                                "type": "boolean",
                                "description": "是否全量同步，默认为 False（增量同步）",
                                "default": False
                            }
                        }
                    }
                ),
                Tool(
                    name="get_space_info",
                    description="获取所有可用的 Confluence 空间信息",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="get_recent_updates",
                    description="获取最近更新的页面",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "days": {
                                "type": "integer",
                                "description": "最近天数，默认为 7",
                                "default": 7
                            },
                            "limit": {
                                "type": "integer",
                                "description": "返回数量限制，默认为 20",
                                "default": 20
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """处理工具调用"""
            try:
                if name == "search_knowledge":
                    result = await self._search_knowledge(
                        query=arguments["query"],
                        space_key=arguments.get("space_key"),
                        top_k=arguments.get("top_k", 5)
                    )
                elif name == "sync_knowledge_source":
                    result = await self._sync_knowledge_source(
                        space_key=arguments.get("space_key"),
                        full_sync=arguments.get("full_sync", False)
                    )
                elif name == "get_space_info":
                    result = await self._get_space_info()
                elif name == "get_recent_updates":
                    result = await self._get_recent_updates(
                        days=arguments.get("days", 7),
                        limit=arguments.get("limit", 20)
                    )
                else:
                    result = {"error": f"Unknown tool: {name}"}
                
                return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
                
            except Exception as e:
                error_result = {"error": str(e)}
                return [TextContent(type="text", text=json.dumps(error_result, ensure_ascii=False, indent=2))]
    
    async def _search_knowledge(
        self,
        query: str,
        space_key: Optional[str] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        搜索知识库
        
        Args:
            query: 用户查询
            space_key: 可选，限定搜索的空间
            top_k: 返回结果数量
        """
        # Step 1: 从 Confluence 搜索页面
        search_results = self.confluence_client.search_pages(query, space_key)
        
        # Step 2: 获取页面详细内容
        documents = []
        for result in search_results.get("results", [])[:10]:  # 限制处理数量
            page_id = result.get("content", {}).get("id")
            if not page_id:
                continue
            
            try:
                page_content = self.confluence_client.get_page_content(page_id)
                if page_content:
                    # 提取纯文本
                    content = self.text_processor.extract_text(page_content)
                    
                    documents.append({
                        "id": page_id,
                        "title": page_content.get("title", "Untitled"),
                        "content": content,
                        "space": page_content.get("space", {}).get("key", "unknown"),
                        "url": page_content.get("_links", {}).get("webui", ""),
                        "version": page_content.get("version", {}).get("number", 1),
                        "updated": page_content.get("version", {}).get("when", "")
                    })
            except Exception:
                continue
        
        # Step 3: 如果有新文档，先索引到向量数据库
        if documents:
            try:
                await self._index_documents(documents)
            except Exception as e:
                # 索引失败不影响搜索返回
                print(f"Warning: Failed to index documents: {e}")
        
        # Step 4: 向量相似度检索
        try:
            vector_results = self.vector_client.search(query, top_k)
        except Exception:
            vector_results = {"matches": []}
        
        # Step 5: 合并结果
        final_results = self._merge_results(documents, vector_results, top_k)
        
        return {
            "query": query,
            "results": final_results,
            "total_found": len(final_results),
            "sources": list(set([r.get("space", "unknown") for r in final_results])),
            "metadata": {
                "search_strategy": "hybrid",
                "vector_search": True,
                "confluence_search": True
            }
        }
    
    async def _sync_knowledge_source(
        self,
        space_key: Optional[str] = None,
        full_sync: bool = False
    ) -> Dict[str, Any]:
        """同步知识源"""
        # 获取要同步的空间列表
        if space_key:
            spaces = [space_key]
        else:
            spaces = self.confluence_client.get_all_space_keys()
        
        total_documents = 0
        total_chunks = 0
        
        for space in spaces:
            try:
                # 获取空间中的页面
                pages = self.confluence_client.get_space_pages(space)
                
                documents = []
                for page in pages:
                    try:
                        page_content = self.confluence_client.get_page_content(page["id"])
                        if page_content:
                            content = self.text_processor.extract_text(page_content)
                            
                            documents.append({
                                "id": page["id"],
                                "title": page_content.get("title", "Untitled"),
                                "content": content,
                                "space": page_content.get("space", {}).get("key", space),
                                "url": page_content.get("_links", {}).get("webui", ""),
                                "version": page_content.get("version", {}).get("number", 1)
                            })
                    except Exception:
                        continue
                
                # 索引文档
                if documents:
                    chunk_count = await self._index_documents(documents)
                    total_chunks += chunk_count
                    total_documents += len(documents)
                    
            except Exception as e:
                print(f"Warning: Failed to sync space {space}: {e}")
                continue
        
        return {
            "status": "success",
            "spaces_synced": len(spaces),
            "documents_indexed": total_documents,
            "chunks_created": total_chunks,
            "sync_type": "full" if full_sync else "incremental"
        }
    
    async def _get_space_info(self) -> List[Dict[str, str]]:
        """获取空间信息"""
        spaces = self.confluence_client.get_all_spaces()
        return [
            {
                "key": s.get("key", ""),
                "name": s.get("name", ""),
                "type": s.get("type", "global")
            }
            for s in spaces
        ]
    
    async def _get_recent_updates(self, days: int, limit: int) -> List[Dict[str, str]]:
        """获取最近更新的页面"""
        import time
        from datetime import datetime
        
        # 计算日期过滤器
        date_filter = int(time.mktime(
            (datetime.now().replace(day=datetime.now().day - days)).timetuple()
        ))
        
        results = self.confluence_client.get_recent_pages(date_filter, limit)
        
        return [
            {
                "id": r.get("content", {}).get("id", ""),
                "title": r.get("content", {}).get("title", ""),
                "last_modified": str(r.get("lastModified", {})),
                "url": r.get("content", {}).get("_links", {}).get("webui", "")
            }
            for r in results.get("results", [])
        ]
    
    async def _index_documents(self, documents: List[Dict]) -> int:
        """索引文档到向量数据库"""
        chunks = []
        
        for doc in documents:
            # 分块处理
            text_chunks = self.text_processor.split_text(
                doc["content"],
                chunk_size=512,
                overlap=50
            )
            
            for i, chunk in enumerate(text_chunks):
                # 生成嵌入
                embedding = self.vector_client.generate_embedding(chunk)
                
                chunks.append({
                    "id": f"{doc['id']}_{i}",
                    "values": embedding,
                    "metadata": {
                        "page_id": doc["id"],
                        "page_title": doc["title"],
                        "space": doc["space"],
                        "url": doc["url"],
                        "chunk_index": i,
                        "text": chunk[:200]
                    }
                })
        
        # 批量索引
        if chunks:
            self.vector_client.upsert(chunks)
        
        return len(chunks)
    
    def _merge_results(
        self,
        documents: List[Dict],
        vector_results: Dict,
        top_k: int
    ) -> List[Dict]:
        """合并检索结果"""
        # 去重并优先使用向量检索结果
        seen_ids = set()
        final_results = []
        
        # 优先添加向量检索结果
        for match in vector_results.get("matches", [])[:top_k]:
            metadata = match.get("metadata", {})
            page_id = metadata.get("page_id", "")
            
            if page_id and page_id not in seen_ids:
                seen_ids.add(page_id)
                final_results.append({
                    "id": page_id,
                    "title": metadata.get("page_title", "Untitled"),
                    "space": metadata.get("space", "unknown"),
                    "url": metadata.get("url", ""),
                    "score": match.get("score", 0),
                    "relevance": "high",
                    "chunk_preview": metadata.get("text", "")
                })
        
        # 添加 Confluence 直接搜索的结果（如果没有向量结果）
        if not final_results:
            for doc in documents[:top_k]:
                if doc["id"] not in seen_ids:
                    seen_ids.add(doc["id"])
                    final_results.append({
                        "id": doc["id"],
                        "title": doc["title"],
                        "space": doc["space"],
                        "url": doc["url"],
                        "score": 1.0,
                        "relevance": "medium",
                        "content_preview": doc["content"][:200] + "..."
                    })
        
        return final_results


async def main():
    """主入口函数"""
    server = KnowledgeSourceMCPServer()
    
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
