"""
Confluence API Client

封装 Confluence Cloud API 的所有操作。
"""

from typing import Any, Dict, List, Optional


class ConfluenceClient:
    """Confluence 客户端"""
    
    def __init__(
        self,
        url: str,
        email: str,
        api_token: str
    ):
        """
        初始化 Confluence 客户端
        
        Args:
            url: Confluence Cloud URL (e.g., https://your-domain.atlassian.net)
            email: 管理员邮箱
            api_token: API Token
        """
        self.url = url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Basic {self._encode_credentials()}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # 延迟初始化 requests 库
        self._requests = None
    
    @property
    def requests(self):
        """延迟加载 requests 库"""
        if self._requests is None:
            import requests
            self._requests = requests
        return self._requests
    
    def _encode_credentials(self) -> str:
        """编码认证信息"""
        import base64
        credentials = f"{self.email}:{self.api_token}"
        return base64.b64encode(credentials.encode()).decode()
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict:
        """发起 API 请求"""
        url = f"{self.url}/wiki/rest/api{endpoint}"
        
        try:
            response = self.requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Confluence API Error: {e}")
            return {"results": [], "error": str(e)}
    
    # ==================== 空间操作 ====================
    
    def get_all_spaces(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取所有空间"""
        result = self._make_request(
            "GET",
            f"/space?limit={limit}&expand=key,homepage"
        )
        return result.get("results", [])
    
    def get_space_info(self, space_key: str) -> Dict[str, Any]:
        """获取空间详情"""
        return self._make_request("GET", f"/space/{space_key}")
    
    def get_space_content(
        self,
        space_key: str,
        start: int = 0,
        limit: int = 25,
        expand: str = "page"
    ) -> Dict[str, Any]:
        """获取空间内容"""
        return self._make_request(
            "GET",
            f"/space/{space_key}/content/{expand}?start={start}&limit={limit}"
        )
    
    def get_space_pages(self, space_key: str) -> List[Dict[str, Any]]:
        """获取空间中的所有页面"""
        all_pages = []
        start = 0
        limit = 100
        
        while True:
            result = self._make_request(
                "GET",
                f"/space/{space_key}/content/page?start={start}&limit={limit}"
            )
            pages = result.get("page", {}).get("results", [])
            
            if not pages:
                break
            
            all_pages.extend(pages)
            
            if len(pages) < limit:
                break
            
            start += limit
        
        return all_pages
    
    def get_all_space_keys(self) -> List[str]:
        """获取所有空间 Key"""
        spaces = self.get_all_spaces()
        return [s.get("key") for s in spaces if s.get("key")]
    
    # ==================== 页面操作 ====================
    
    def get_page_by_id(
        self,
        page_id: str,
        expand: str = "body.storage,version,space"
    ) -> Dict[str, Any]:
        """根据 ID 获取页面"""
        return self._make_request(
            "GET",
            f"/content/{page_id}?expand={expand}"
        )
    
    def get_page_content(self, page_id: str) -> Optional[Dict[str, Any]]:
        """获取页面完整内容"""
        try:
            return self.get_page_by_id(page_id)
        except Exception:
            return None
    
    def get_page_children(self, page_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取页面子页面"""
        result = self._make_request(
            "GET",
            f"/content/{page_id}/child/page?limit={limit}"
        )
        return result.get("results", [])
    
    def get_page_ancestors(self, page_id: str) -> List[Dict[str, Any]]:
        """获取页面祖先路径"""
        result = self._make_request(
            "GET",
            f"/content/{page_id}/ancestor"
        )
        return result.get("results", [])
    
    # ==================== 搜索操作 ====================
    
    def search_pages(
        self,
        query: str,
        space_key: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        使用 CQL 搜索页面
        
        Args:
            query: 搜索关键词
            space_key: 可选，限定空间
            limit: 返回数量限制
        """
        # 构建 CQL 查询
        cql = f'text ~ "{query}"'
        if space_key:
            cql += f' AND space = "{space_key}"'
        
        cql += ' AND type = page ORDER BY lastmodified DESC'
        
        params = {
            "cql": cql,
            "limit": limit,
            "expand": "content.version,content.space"
        }
        
        return self._make_request("GET", "/content/search", params=params)
    
    def get_recent_pages(
        self,
        since_timestamp: int,
        limit: int = 20
    ) -> Dict[str, Any]:
        """获取最近更新的页面"""
        cql = f'lastmodified >= {since_timestamp} ORDER BY lastmodified DESC'
        
        params = {
            "cql": cql,
            "limit": limit,
            "expand": "content.version,content.space"
        }
        
        return self._make_request("GET", "/content/search", params=params)
    
    # ==================== 附件操作 ====================
    
    def get_attachments_from_page(self, page_id: str) -> List[Dict[str, Any]]:
        """获取页面附件"""
        result = self._make_request(
            "GET",
            f"/content/{page_id}/child/attachment"
        )
        return result.get("results", [])
    
    def get_attachment_content(self, attachment_id: str) -> bytes:
        """获取附件内容"""
        url = f"{self.url}/wiki/rest/api/content/{attachment_id}/download"
        
        response = self.requests.get(
            url,
            headers=self.headers,
            timeout=30
        )
        response.raise_for_status()
        return response.content
    
    # ==================== 标签操作 ====================
    
    def get_labels(self, page_id: str) -> List[Dict[str, str]]:
        """获取页面标签"""
        result = self._make_request(
            "GET",
            f"/content/{page_id}/label"
        )
        return result
    
    def add_label(self, page_id: str, label: str) -> bool:
        """添加标签"""
        url = f"{self.url}/wiki/rest/api/content/{page_id}/label"
        
        try:
            response = self.requests.post(
                url,
                headers=self.headers,
                json=[{"prefix": "global", "name": label}],
                timeout=30
            )
            return response.status_code in [200, 201]
        except Exception:
            return False
