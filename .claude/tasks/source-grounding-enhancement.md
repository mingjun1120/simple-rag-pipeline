# Source Grounding Enhancement for RAG Pipeline

## Objective
Enhance the RAG pipeline to provide detailed source attribution for every generated answer, including document name, page number, and specific text chunks used as grounding.

## Research Findings
Based on research into Docling's capabilities:
- DocChunk.meta.doc_items contains provenance information with page numbers and bounding boxes
- Current implementation only uses filename and chunk index, missing rich metadata
- Page numbers available via `chunk.meta.doc_items[0].prov[0].page_no`
- Bounding box coordinates available for visual grounding
- Need to preserve metadata through entire RAG pipeline

## Current State Analysis

### Current Data Flow
1. **Indexer**: Creates chunks with basic source info (`filename:chunk_index`)
2. **Datastore**: Stores content, basic source, embeddings
3. **Retriever**: Returns only content strings, losing source metadata
4. **ResponseGenerator**: Gets content without source attribution
5. **Output**: Response without grounding information

### Current Limitations
- Page numbers not extracted from Docling metadata
- Source information lost during retrieval
- No structured source attribution in responses
- Missing visual grounding capabilities

## Proposed Solution Architecture

### Enhanced Data Structures

```python
# Enhanced DataItem with rich metadata
@dataclass
class DataItem(BaseModel):
    content: str = ""
    source: str = ""
    metadata: Optional[Dict] = None  # New field for rich source info

# New SearchResult structure for retrieval
@dataclass
class SearchResult:
    content: str
    source: str
    page_no: Optional[int] = None
    headings: Optional[List[str]] = None
    bbox: Optional[Dict] = None
    relevance_score: float = 0.0

# Enhanced response structure
@dataclass
class GroundedResponse:
    answer: str
    sources: List[SearchResult]
    formatted_citations: str
```

## Implementation Plan

### Phase 1: Research & Preparation ✓
- [x] Research Docling metadata extraction capabilities
- [x] Analyze current data flow and limitations
- [x] Design enhanced data structures

### Phase 2: Core Infrastructure Updates

#### Task 2.1: Update Data Models
- [ ] Modify `DataItem` in `base_datastore.py` to include metadata field
- [ ] Create `SearchResult` class for structured retrieval results
- [ ] Update database schema to store additional metadata

#### Task 2.2: Enhance Indexer Component
**File**: `src/impl/indexer.py`
- [ ] Extract page numbers from `chunk.meta.doc_items[0].prov[0].page_no`
- [ ] Extract bounding box coordinates for visual grounding
- [ ] Preserve section headings and document structure
- [ ] Create structured metadata dictionary
- [ ] Update `_items_from_chunks()` method

**Expected Changes**:
```python
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
        content_headings = "## " + ", ".join(chunk.meta.headings)
        content_text = f"{content_headings}\n{chunk.text}"
        
        # Enhanced source string with page info
        source = f"{chunk.meta.origin.filename}:page_{page_no}:chunk_{i}"
        
        item = DataItem(
            content=content_text,
            source=source,
            metadata=metadata
        )
        items.append(item)
    return items
```

### Phase 3: Update Storage and Retrieval

#### Task 3.1: Enhance Datastore
**File**: `src/impl/datastore.py`
- [ ] Update database schema to store metadata JSON
- [ ] Modify `add_items()` to handle metadata field
- [ ] Update `search()` to return structured results with metadata

#### Task 3.2: Update Base Interfaces
**Files**: `src/interface/base_datastore.py`, `src/interface/base_retriever.py`
- [ ] Update `BaseDatastore.search()` return type to `List[SearchResult]`
- [ ] Update `BaseRetriever.search()` return type to `List[SearchResult]`
- [ ] Ensure backward compatibility

#### Task 3.3: Enhance Retriever
**File**: `src/impl/retriever.py`
- [ ] Return `SearchResult` objects instead of content strings
- [ ] Include relevance scores from Cohere re-ranking
- [ ] Preserve all source metadata through retrieval process

### Phase 4: Response Generation Enhancement

#### Task 4.1: Update Response Generator Interface
**File**: `src/interface/base_response_generator.py`
- [ ] Change `generate_response()` to accept `List[SearchResult]`
- [ ] Return structured response with grounding information

#### Task 4.2: Enhance Response Generation
**File**: `src/impl/response_generator.py`
- [ ] Modify to work with `SearchResult` objects
- [ ] Generate formatted citations
- [ ] Create clear source attribution in responses

**Expected Response Format**:
```
Answer: [Generated response based on retrieved information]

Sources Used:
1. Document: sl_tourist_guide.pdf, Page: 5, Section: "Hotels and Accommodations"
   Text: "The Lagoon Breeze Hotel opened in 1995 and features 120 luxury rooms..."

2. Document: sl_booklet.pdf, Page: 12, Section: "Island Overview"  
   Text: "Located on the pristine shores of the northern coast..."
```

### Phase 5: Pipeline Integration

#### Task 5.1: Update RAG Pipeline
**File**: `src/rag_pipeline.py`
- [ ] Update `process_query()` to handle new data structures
- [ ] Modify result display to show source grounding
- [ ] Update evaluation flow to work with enhanced responses

#### Task 5.2: Update Main CLI
**File**: `main.py`
- [ ] Ensure CLI commands work with enhanced output format
- [ ] Update query result display to show grounding information

### Phase 6: Testing and Validation

#### Task 6.1: Unit Testing
- [ ] Test indexer metadata extraction with sample PDFs
- [ ] Verify datastore metadata storage and retrieval
- [ ] Test response generation with source attribution

#### Task 6.2: Integration Testing
- [ ] Run full pipeline with sample queries
- [ ] Verify grounding accuracy with `sample_data/eval/sample_questions.json`
- [ ] Test with different document types and structures

#### Task 6.3: User Experience Testing
- [ ] Validate citation format readability
- [ ] Test with complex multi-document queries
- [ ] Ensure performance impact is minimal

## Technical Considerations

### Database Schema Changes
- Add `metadata` JSON column to LanceDB schema
- Maintain backward compatibility with existing data
- Consider migration strategy for existing embeddings

### Performance Impact
- Additional metadata storage will increase memory usage
- Retrieval operations may be slightly slower
- Consider caching frequently accessed metadata

### Error Handling
- Handle PDFs without page information gracefully
- Fallback to basic source attribution when metadata unavailable
- Validate metadata structure before storage

## Success Criteria

1. **Accuracy**: Every response includes specific document, page, and text chunk references
2. **Completeness**: All relevant sources are cited with proper attribution
3. **Readability**: Source information is clearly formatted and easy to understand
4. **Performance**: Less than 20% performance degradation in query response time
5. **Robustness**: System handles various document formats and edge cases

## Risks and Mitigations

### Risk 1: Breaking Changes to Existing Interfaces
**Mitigation**: Implement gradual migration with backward compatibility layers

### Risk 2: Performance Degradation
**Mitigation**: Profile metadata operations and optimize storage/retrieval

### Risk 3: Complex Citation Formatting
**Mitigation**: Create configurable citation templates, start with simple format

## Next Steps

1. **Get approval** for this implementation plan
2. **Start with Phase 2**: Core infrastructure updates
3. **Incremental testing** after each component update
4. **Update plan** as implementation progresses with detailed change logs

---

## Implementation Log
*This section will be updated as work progresses*

### Changes Made:
- [Timestamp] [Component] [Description of changes]

### Lessons Learned:
- [Implementation insights and discoveries]

### Next Handover Tasks:
- [Tasks ready for other engineers]