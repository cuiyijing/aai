# Agentic RAG - Confluence Knowledge Base

基于 MCP (Model Context Protocol) 的企业知识库问答系统。

## 架构概述

```
┌─────────────────────────────────────────────────────────┐
│                   用户交互层                             │
│         (Web UI / Slack Bot / API / Claude Desktop)      │
└──────────────────┬──────────────────────────────────────┘
                   │ 
┌──────────────────▼──────────────────────────────────────┐
│                 单代理控制器 (Agent)                     │
│                                                         │
│   用户查询 → 意图理解 → 知识检索 → 响应生成              │
│                                                         │
└──────────────────┬──────────────────────────────────────┘
                   │ MCP Protocol
┌──────────────────▼──────────────────────────────────────┐
│                  MCP 服务器层                           │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │         MCP Server - Knowledge Source            │  │
│  │                                                   │  │
│  │   Tool: search_knowledge(query: str)             │  │
│  │   ├── Confluence API 调用                        │  │
│  │   ├── 文本提取与分块                              │  │
│  │   ├── 向量嵌入生成                               │  │
│  │   └── 向量相似度检索                             │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│                   数据服务层                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Confluence   │  │ Vector Store │  │ Cache        │    │
│  │ Cloud API    │  │ (Pinecone)   │  │ (Redis)      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## 项目结构

```
agentic_rag/
├── mcp_servers/
│   └── knowledge_source/
│       ├── __init__.py
│       ├── server.py              # MCP Server (统一入口)
│       ├── confluence_client.py   # Confluence API 封装
│       ├── vector_client.py       # 向量数据库封装
│       └── text_processor.py      # 文本处理工具
│
├── agents/
│   └── knowledge_agent.py         # 单代理实现
│
├── config/
│   └── mcp_config.json            # MCP 配置
│
├── requirements.txt               # Python 依赖
└── README.md                      # 本文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件或设置环境变量：

```bash
export CONFLUENCE_URL="https://your-domain.atlassian.net"
export CONFLUENCE_EMAIL="your-email@company.com"
export CONFLUENCE_API_TOKEN="your-api-token"
export PINECONE_API_KEY="your-pinecone-api-key"
export PINECONE_HOST="https://xxx.pinecone.io"
export OPENAI_API_KEY="your-openai-api-key"
```

### 3. 配置 MCP

在 Claude Desktop 或其他 MCP Client 中添加配置：

```json
{
  "mcpServers": {
    "knowledge-source": {
      "command": "python",
      "args": ["-m", "agentic_rag.mcp_servers.knowledge_source.server"],
      "env": {
        "CONFLUENCE_URL": "https://your-domain.atlassian.net",
        "CONFLUENCE_EMAIL": "your-email@company.com",
        "CONFLUENCE_API_TOKEN": "${CONFLUENCE_API_TOKEN}",
        "PINECONE_API_KEY": "${PINECONE_API_KEY}",
        "PINECONE_HOST": "https://xxx.pinecone.io",
        "OPENAI_API_KEY": "${OPENAI_API_KEY}"
      }
    }
  }
}
```

## MCP Tools

### search_knowledge
搜索 Confluence 知识库。

```json
{
  "query": "项目部署流程",
  "space_key": "PROJECTS",
  "top_k": 5
}
```

### sync_knowledge_source
同步 Confluence 知识源到向量数据库。

```json
{
  "space_key": "PROJECTS",
  "full_sync": false
}
```

### get_space_info
获取所有可用的 Confluence 空间信息。

```json
{}
```

### get_recent_updates
获取最近更新的页面。

```json
{
  "days": 7,
  "limit": 20
}
```

## 功能特性

- ✅ **统一 MCP 接口** - 将 Confluence 知识库封装为单一 Tool
- ✅ **混合检索** - 支持 Confluence 原生搜索 + 向量相似度检索
- ✅ **智能分块** - 自动分块和嵌入生成
- ✅ **增量同步** - 支持增量更新向量索引
- ✅ **查询理解** - 支持意图分析和关键词提取
- ✅ **源文档引用** - 返回源文档链接和元数据

## 技术栈

- **MCP** - Model Context Protocol
- **Confluence Cloud API** - 企业知识库
- **Pinecone** - 向量数据库
- **OpenAI text-embedding-3-small** - 嵌入生成
- **Python 3.10+** - 开发语言

## 许可证

MIT License
