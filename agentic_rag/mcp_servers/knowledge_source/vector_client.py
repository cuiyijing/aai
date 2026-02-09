"""
Vector Store Client

向量存储客户端，支持 Pinecone 或兼容的向量数据库。
"""

from typing import Any, Dict, List, Optional
from openai import OpenAI


class VectorStoreClient:
    """向量存储客户端"""
    
    def __init__(
        self,
        api_key: str,
        host: str,
        openai_api_key: str,
        namespace: str = "confluence-knowledge"
    ):
        """
        初始化向量存储客户端
        
        Args:
            api_key: Pinecone API Key
            host: Pinecone Index Host
            openai_api_key: OpenAI API Key (用于生成嵌入)
            namespace: 命名空间
        """
        self.api_key = api_key
        self.host = host
        self.namespace = namespace
        
        # 初始化 OpenAI 客户端
        self.openai = OpenAI(api_key=openai_api_key)
        
        # 初始化 Pinecone
        from pinecone import Pinecone
        self.pinecone = Pinecone(api_key=api_key)
        self.index = self.pinecone.Index(host=host)
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        使用 OpenAI 生成文本嵌入
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量
        """
        response = self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        namespace: Optional[str] = None,
        score_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        执行向量相似度搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            namespace: 可选，覆盖默认命名空间
            score_threshold: 可选，过滤低相似度结果
            
        Returns:
            搜索结果
        """
        # 生成查询向量
        query_vector = self.generate_embedding(query)
        
        # 执行搜索
        search_params = {
            "vector": query_vector,
            "top_k": top_k,
            "include_metadata": True,
            "include_values": False
        }
        
        if namespace:
            search_params["namespace"] = namespace
        elif self.namespace:
            search_params["namespace"] = self.namespace
        
        try:
            result = self.index.query(**search_params)
            
            # 过滤低相似度结果
            if score_threshold is not None:
                matches = [
                    m for m in result.get("matches", [])
                    if m.get("score", 0) >= score_threshold
                ]
                result["matches"] = matches
            
            return result
            
        except Exception as e:
            print(f"Vector Search Error: {e}")
            return {"matches": [], "error": str(e)}
    
    def upsert(
        self,
        vectors: List[Dict[str, Any]],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        批量插入向量
        
        Args:
            vectors: 向量列表，每个包含 id, values, metadata
            namespace: 可选，覆盖默认命名空间
            
        Returns:
            API 响应
        """
        if not vectors:
            return {"status": "empty", "count": 0}
        
        upsert_params = {
            "vectors": vectors,
            "namespace": namespace or self.namespace
        }
        
        try:
            result = self.index.upsert(**upsert_params)
            return {
                "status": "success",
                "count": len(vectors),
                "upserted_count": result.get("upsertedCount", 0)
            }
        except Exception as e:
            print(f"Vector Upsert Error: {e}")
            return {"error": str(e)}
    
    def delete(
        self,
        ids: Optional[List[str]] = None,
        namespace: Optional[str] = None,
        delete_all: bool = False
    ) -> Dict[str, Any]:
        """
        删除向量
        
        Args:
            ids: 要删除的向量 ID 列表
            namespace: 命名空间
            delete_all: 是否删除命名空间下所有向量
            
        Returns:
            API 响应
        """
        try:
            if delete_all:
                result = self.index.delete_all(
                    namespace=namespace or self.namespace
                )
            elif ids:
                result = self.index.delete(
                    ids=ids,
                    namespace=namespace or self.namespace
                )
            else:
                return {"error": "Must provide ids or delete_all=True"}
            
            return {"status": "success", "details": str(result)}
            
        except Exception as e:
            print(f"Vector Delete Error: {e}")
            return {"error": str(e)}
    
    def fetch(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取指定 ID 的向量
        
        Args:
            ids: 向量 ID 列表
            namespace: 命名空间
            
        Returns:
            向量数据
        """
        try:
            result = self.index.fetch(
                ids=ids,
                namespace=namespace or self.namespace
            )
            return result
            
        except Exception as e:
            print(f"Vector Fetch Error: {e}")
            return {"vectors": {}, "error": str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        try:
            return self.index.describe_index_stats()
        except Exception as e:
            print(f"Index Stats Error: {e}")
            return {"error": str(e)}
    
    def update_metadata(
        self,
        id: str,
        metadata: Dict[str, Any],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新向量元数据
        
        Args:
            id: 向量 ID
            metadata: 新的元数据
            namespace: 命名空间
            
        Returns:
            API 响应
        """
        try:
            result = self.index.update(
                id=id,
                set_metadata=metadata,
                namespace=namespace or self.namespace
            )
            return {"status": "success", "result": str(result)}
        except Exception as e:
            print(f"Vector Update Error: {e}")
            return {"error": str(e)}
    
    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成嵌入
        
        Args:
            texts: 文本列表
            
        Returns:
            嵌入向量列表
        """
        if not texts:
            return []
        
        # 批量处理，避免超出限制
        embeddings = []
        batch_size = 100
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            response = self.openai.embeddings.create(
                model="text-embedding-3-small",
                input=batch
            )
            
            embeddings.extend([
                data.embedding for data in response.data
            ])
        
        return embeddings
    
    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        alpha: float = 0.5,
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        混合搜索（向量 + 关键词）
        需要 Pinecone 混合搜索支持
        
        Args:
            query: 查询文本
            top_k: 返回数量
            alpha: 0=纯关键词，1=纯向量，0.5=混合
            namespace: 命名空间
            
        Returns:
            混合搜索结果
        """
        try:
            query_vector = self.generate_embedding(query)
            
            result = self.index.query(
                vector=query_vector,
                top_k=top_k,
                alpha=alpha,
                include_metadata=True,
                namespace=namespace or self.namespace
            )
            
            return result
            
        except Exception as e:
            print(f"Hybrid Search Error: {e}")
            return {"matches": [], "error": str(e)}
