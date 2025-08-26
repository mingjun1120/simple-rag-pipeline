from abc import ABC, abstractmethod
from typing import List
from .base_datastore import SearchResult


class BaseResponseGenerator(ABC):

    @abstractmethod
    def generate_response(self, query: str, search_results: List[SearchResult]) -> str:
        pass
