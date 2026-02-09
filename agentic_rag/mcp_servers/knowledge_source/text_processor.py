"""
Text Processor

文本处理工具，包括 HTML 解析、文本分块等功能。
"""

import re
from typing import List


class TextProcessor:
    """文本处理器"""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def extract_text(self, confluence_page: dict) -> str:
        """从 Confluence 页面提取纯文本"""
        body = confluence_page.get("body", {})
        storage = body.get("storage", {})
        html_content = storage.get("value", "")
        
        if not html_content:
            return ""
        
        text = self._remove_html_tags(html_content)
        text = self._clean_whitespace(text)
        
        return text.strip()
    
    def _remove_html_tags(self, html: str) -> str:
        """移除 HTML 标签"""
        html = html.replace("&nbsp;", " ")
        html = html.replace("&", "&")
        html = html.replace("<", "<")
        html = html.replace(">", ">")
        html = html.replace(""", '"')
        html = html.replace("&#39;", "'")
        
        pattern = r"<[^>]+>"
        text = re.sub(pattern, "", html)
        
        text = text.replace("\n\n", "\n")
        
        return text
    
    def _clean_whitespace(self, text: str) -> str:
        """清理空白字符"""
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join([line for line in lines if line])
        return text
    
    def split_text(self, text: str, chunk_size: int = None, 
                   chunk_overlap: int = None) -> List[str]:
        """智能分块文本"""
        chunk_size = chunk_size or self.chunk_size
        chunk_overlap = chunk_overlap or self.chunk_overlap
        
        if not text:
            return []
        
        paragraphs = self._split_by_paragraphs(text)
        
        if not paragraphs:
            return []
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            
            if len(paragraph) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                
                chunks.extend(self._split_long_text(paragraph, chunk_size))
                continue
            
            if len(current_chunk) + len(paragraph) + 2 > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                
                if chunk_overlap > 0 and chunks:
                    overlap_text = chunks[-1][-chunk_overlap:]
                    current_chunk = overlap_text + " " + paragraph
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk = current_chunk + "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _split_by_paragraphs(self, text: str) -> List[str]:
        """按段落分割文本"""
        paragraphs = re.split(r"\n{2,}", text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        return paragraphs
    
    def _split_long_text(self, text: str, chunk_size: int) -> List[str]:
        """分割长文本"""
        chunks = []
        sentences = self._split_by_sentences(text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            
            if not chunks:
                chunks.append(sentence)
                continue
            
            last_chunk = chunks[-1]
            if len(last_chunk) + len(sentence) + 1 > chunk_size:
                chunks.append(sentence)
            else:
                chunks[-1] = last_chunk + " " + sentence
        
        return chunks
    
    def _split_by_sentences(self, text: str) -> List[str]:
        """按句子分割文本"""
        pattern = r"(?<=[.!?])\s+"
        sentences = re.split(pattern, text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    def extract_metadata(self, confluence_page: dict) -> dict:
        """从 Confluence 页面提取元数据"""
        version = confluence_page.get("version", {})
        space = confluence_page.get("space", {})
        links = confluence_page.get("_links", {})
        
        return {
            "page_id": confluence_page.get("id"),
            "title": confluence_page.get("title"),
            "space_key": space.get("key"),
            "space_name": space.get("name"),
            "version": version.get("number"),
            "updated": version.get("when"),
            "url": links.get("webui"),
            "ancestry": self._get_ancestry(confluence_page.get("ancestors", []))
        }
    
    def _get_ancestry(self, ancestors: list) -> str:
        """获取页面层级路径"""
        if not ancestors:
            return ""
        
        paths = [a.get("title", "") for a in ancestors]
        return " > ".join(paths)
    
    def truncate_for_preview(self, text: str, max_length: int = 200) -> str:
        """截取文本预览"""
        if len(text) <= max_length:
            return text
        
        return text[:max_length].strip() + "..."
    
    def clean_for_embedding(self, text: str) -> str:
        """清理用于生成嵌入的文本"""
        text = re.sub(r"[^\w\s.,!?;:\'-]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
