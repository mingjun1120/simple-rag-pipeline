from typing import List
from interface.base_response_generator import BaseResponseGenerator
from interface.base_datastore import SearchResult
from util.invoke_ai import invoke_ai


SYSTEM_PROMPT = """
Use the provided context to provide a concise answer to the user's question.
If you cannot find the answer in the context, say so. Do not make up information.
"""


class ResponseGenerator(BaseResponseGenerator):
    def generate_response(self, query: str, search_results: List[SearchResult]) -> str:
        """Generate a response with source grounding using SearchResult objects."""
        
        # Combine context into a single string (simple approach like original)
        context_text = "\n".join([result.content for result in search_results])
        user_message = (
            f"<context>\n{context_text}\n</context>\n"
            f"<question>\n{query}\n</question>"
        )

        # Get AI response
        ai_response = invoke_ai(system_message=SYSTEM_PROMPT, user_message=user_message)
        
        # Format with source citations
        formatted_response = self._format_response_with_sources(ai_response, search_results)
        
        return formatted_response
    
    def _format_response_with_sources(self, ai_response: str, search_results: List[SearchResult]) -> str:
        """Format the response with detailed source citations."""
        
        # Create source citations
        sources_section = "\n\nSources Used:"
        for i, result in enumerate(search_results, 1):
            # Extract filename from source
            filename = result.source.split(':')[0] if result.source else "Unknown Document"
            
            # Format page number
            page_info = f", Page: {result.page_no}" if result.page_no else ""
            
            # Format section headings
            section_info = ""
            if result.headings:
                section_info = f", Section: \"{' > '.join(result.headings)}\""
            
            # Format relevance score
            score_info = f" (Relevance: {result.relevance_score:.3f})" if result.relevance_score > 0 else ""
            
            # Truncate content for display (first 150 characters)
            display_content = result.content[:150] + "..." if len(result.content) > 150 else result.content
            display_content = display_content.replace('\n', ' ')  # Single line
            
            citation = (
                f"\n{i}. Document: {filename}{page_info}{section_info}{score_info}\n"
                f"   Text: \"{display_content}\""
            )
            sources_section += citation
        
        return ai_response + sources_section
