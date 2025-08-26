from interface.base_datastore import BaseDatastore, SearchResult
from interface.base_retriever import BaseRetriever
from typing import List
from dotenv import load_dotenv
import cohere
import os

load_dotenv()

class Retriever(BaseRetriever):
    def __init__(self, datastore: BaseDatastore):
        self.datastore = datastore

    def search(self, query: str, top_k: int = 3) -> List[SearchResult]:
        search_results = self.datastore.search(query, top_k=top_k * 3)
        reranked_results = self._rerank(query, search_results, top_k=top_k)
        return reranked_results

    def _rerank(self, query: str, search_results: List[SearchResult], top_k: int = 10) -> List[SearchResult]:
        co = cohere.ClientV2(api_key=os.getenv("CO_API_KEY"))
        
        # Extract content for reranking
        documents = [result.content for result in search_results]
        
        response = co.rerank(
            model="rerank-v3.5",
            query=query,
            documents=documents,
            top_n=top_k,
        )

        # Update relevance scores and return reranked SearchResult objects
        reranked_results = []
        for result in response.results:
            search_result = search_results[result.index]
            # Update relevance score from Cohere
            search_result.relevance_score = result.relevance_score
            reranked_results.append(search_result)
        
        result_indices = [result.index for result in response.results]
        print(f"✅ Reranked Indices: {result_indices}")
        return reranked_results
