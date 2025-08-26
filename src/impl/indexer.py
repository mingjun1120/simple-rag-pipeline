import os
import tiktoken
from typing import List
from interface.base_datastore import DataItem
from interface.base_indexer import BaseIndexer
from docling.chunking import HybridChunker, DocChunk
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer

class Indexer(BaseIndexer):
    def __init__(self):
        self.converter = DocumentConverter()
        
        tokenizer = OpenAITokenizer(tokenizer=tiktoken.encoding_for_model("gpt-4o"), max_tokens=128 * 1024)
        self.chunker = HybridChunker(tokenizer=tokenizer, max_tokens=8192)
        
        # Disable tokenizers parallelism to avoid OOM errors.
        os.environ["TOKENIZERS_PARALLELISM"] = "false"

    def index(self, document_paths: List[str]) -> List[DataItem]:
        items = []
        for document_path in document_paths:
            document = self.converter.convert(document_path).document
            chunks: List[DocChunk] = self.chunker.chunk(document)
            items.extend(self._items_from_chunks(chunks))
        return items

    def _items_from_chunks(self, chunks: List[DocChunk]) -> List[DataItem]:
        items = []
        for i, chunk in enumerate(chunks):
            # Extract page and location info
            page_no = None
            bbox = None
            if chunk.meta.doc_items and chunk.meta.doc_items[0].prov:
                prov = chunk.meta.doc_items[0].prov[0]
                page_no = prov.page_no
                bbox = prov.bbox.__dict__ if prov.bbox else None
            
            # Create rich metadata
            metadata = {
                "page_no": page_no,
                "bbox": bbox,
                "headings": chunk.meta.headings,
                "chunk_index": i,
                "filename": chunk.meta.origin.filename if chunk.meta.origin else None
            }

            # Enrich the chunk
            content_headings = "## " + ", ".join(chunk.meta.headings) if chunk.meta.headings else ""
            content_text = f"{content_headings}\n{chunk.text}" if content_headings else chunk.text
            
            # Enhanced source string with page info
            filename = chunk.meta.origin.filename if chunk.meta.origin else "unknown"
            source = f"{filename}:page_{page_no}:chunk_{i}" if page_no is not None else f"{filename}:chunk_{i}"
            
            item = DataItem(
                content=content_text,
                source=source,
                metadata=metadata
            )
            items.append(item)

        return items
