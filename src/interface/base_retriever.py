from abc import ABC, abstractmethod
from typing import List
from .base_datastore import SearchResult


class BaseRetriever(ABC):

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        pass
