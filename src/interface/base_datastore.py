from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from pydantic import BaseModel
from dataclasses import dataclass


class DataItem(BaseModel):
    content: str = ""
    source: str = ""
    metadata: Optional[Dict] = None


@dataclass
class SearchResult:
    content: str
    source: str
    page_no: Optional[int] = None
    headings: Optional[List[str]] = None
    bbox: Optional[Dict] = None
    relevance_score: float = 0.0


class BaseDatastore(ABC):
    @abstractmethod
    def add_items(self, items: List[DataItem]) -> None:
        pass

    @abstractmethod
    def get_vector(self, content: str) -> List[float]:
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        pass
