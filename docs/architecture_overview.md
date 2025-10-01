# Overall Architecture Analysis

## System Overview
This is a **modular RAG (Retrieval Augmented Generation) pipeline** that demonstrates enterprise-grade document processing, semantic search, and AI-powered response generation. The architecture follows **clean architecture principles** with strict interface-based component boundaries.

---

## Architectural Patterns

### 1. Interface-Driven Design
All core components implement abstract base classes defined in `src/interface/`:
- `base_datastore.py` - Vector storage contract with `add_items()`, `search()`, `get_vector()`
- `base_indexer.py` - Document processing contract with `index()`
- `base_retriever.py` - Search contract with `search()`
- `base_response_generator.py` - Response generation contract with `generate_response()`
- `base_evaluator.py` - Evaluation contract with `evaluate()`

### 2. Dependency Injection
Components are instantiated and injected in `main.py:20-27`:
```python
datastore = Datastore()
indexer = Indexer()
retriever = Retriever(datastore=datastore)  # Injected dependency
response_generator = ResponseGenerator()
evaluator = Evaluator()
```

### 3. Concurrent Processing
- **Embeddings generation**: ThreadPoolExecutor with 8 workers in `datastore.py:77`
- **Batch evaluation**: ThreadPoolExecutor with 10 workers in `rag_pipeline.py:58`

### 4. Configuration-Driven Behavior
- AI provider selection via `config.yml` (azure_openai/cerebras)
- Centralized AI invocation in `util/invoke_ai.py` reads config at runtime

---

## Component Architecture

### Core Components & Responsibilities

#### 1. RAGPipeline (`src/rag_pipeline.py`)
- **Role**: Main orchestrator coordinating all components
- **Dependencies**: Requires all 5 component interfaces (4 required + 1 optional evaluator)
- **Key methods**:
  - `reset()` - Clears vector database
  - `add_documents()` - Orchestrates indexing → storage
  - `process_query()` - Orchestrates retrieval → generation
  - `evaluate()` - Concurrent evaluation of Q&A pairs

#### 2. Datastore (`src/impl/datastore.py`)
- **Role**: Vector database operations and embeddings generation
- **Technology**: LanceDB with PyArrow schema at `data/sample-lancedb/rag-table`
- **External dependencies**:
  - Azure OpenAI (text-embedding-3-small, 1536 dimensions) via `datastore.py:24-28`
  - Gemini embeddings (backup option) via `datastore.py:30`
- **Key features**:
  - Merge-insert operations for idempotent updates (`datastore.py:80-82`)
  - JSON metadata storage (page numbers, headings, bounding boxes)
  - Parallel embedding generation

#### 3. Indexer (`src/impl/indexer.py`)
- **Role**: Document processing and chunking
- **Technology**: Docling with HybridChunker + tiktoken (GPT-4o tokenizer)
- **Configuration**: 8192 max tokens per chunk (`indexer.py:15`)
- **Metadata extraction**:
  - Page numbers and bounding boxes from PDF provenance
  - Heading hierarchies for context (`indexer.py:31-46`)
  - Enhanced source strings: `filename:page_X:chunk_Y`
- **Content enrichment**: Prepends headings to chunk text for better LLM understanding

#### 4. Retriever (`src/impl/retriever.py`)
- **Role**: Two-stage retrieval with re-ranking
- **Dependencies**: Requires BaseDatastore interface
- **Strategy**:
  - Stage 1: Fetch `top_k * 3` results via vector similarity
  - Stage 2: Cohere re-ranking (rerank-v3.5) to select final `top_k` (`retriever.py:19-42`)
- **External dependency**: Cohere API for semantic re-ranking

#### 5. ResponseGenerator (`src/impl/response_generator.py`)
- **Role**: AI-powered response generation with source citation
- **Dependencies**: Uses `invoke_ai` utility for provider-agnostic LLM calls
- **Process**:
  1. Concatenates search results as context
  2. Invokes AI with system prompt + user query
  3. Appends detailed source citations with metadata (`response_generator.py:32-62`)
- **Source citation format**: Document name, page, section headings, relevance score, text preview

#### 6. Evaluator (`src/impl/evaluator.py`)
- **Role**: AI-based correctness evaluation
- **Process**:
  1. Sends question/response/expected_answer to LLM
  2. Extracts structured reasoning and true/false result via XML tags
  3. Returns EvaluationResult object (`evaluator.py:40-46`)

---

## Dependency Graph

```
main.py (CLI Entry Point)
  └─> RAGPipeline (Orchestrator)
       ├─> Datastore (implements BaseDatastore)
       │    └─> Azure OpenAI Embeddings API
       │    └─> Gemini Embeddings API (optional)
       │
       ├─> Indexer (implements BaseIndexer)
       │    └─> Docling DocumentConverter
       │    └─> HybridChunker with OpenAI Tokenizer
       │
       ├─> Retriever (implements BaseRetriever)
       │    ├─> Datastore (injected dependency)
       │    └─> Cohere Re-ranking API
       │
       ├─> ResponseGenerator (implements BaseResponseGenerator)
       │    └─> invoke_ai utility
       │         ├─> Azure OpenAI Chat API (gpt-5-mini)
       │         └─> Cerebras API (gpt-oss-120b)
       │
       └─> Evaluator (implements BaseEvaluator)
            └─> invoke_ai utility
```

---

## Data Flow

### Indexing Flow (`python main.py add`)
1. `main.py:51-53` - CLI collects document paths
2. `rag_pipeline.py:28-32` - Pipeline delegates to indexer → datastore
3. `indexer.py:20-26` - Docling converts PDFs → chunks with metadata
4. `datastore.py:74-82` - Parallel embedding generation → LanceDB merge-insert

### Query Flow (`python main.py query`)
1. `main.py:61-62` - CLI passes query to pipeline
2. `rag_pipeline.py:34-51` - Pipeline orchestrates:
   - Retriever.search() → Get top 3 re-ranked results
   - ResponseGenerator.generate_response() → AI response + citations
3. `retriever.py:14-17` - Two-stage retrieval:
   - Datastore vector search (9 candidates)
   - Cohere re-ranking (top 3)
4. `response_generator.py:14-30` - Response generation:
   - Construct context from search results
   - invoke_ai with system/user messages
   - Append source citations

### Evaluation Flow (`python main.py evaluate`)
1. `main.py:55-59` - Load sample questions JSON
2. `rag_pipeline.py:53-77` - Concurrent evaluation:
   - ThreadPoolExecutor maps questions to `_evaluate_single_question()`
   - Each question triggers full query flow
   - Evaluator compares response vs expected answer
3. `evaluator.py:20-46` - AI judgment with structured output

---

## Utility Layer

### invoke_ai (`src/util/invoke_ai.py`)
- Centralized AI invocation with provider abstraction
- Reads `config.yml` at runtime
- Supports Azure OpenAI (with reasoning_effort) and Cerebras
- Used by ResponseGenerator and Evaluator

### extract_xml (`src/util/extract_xml.py`)
- Simple XML tag extraction for structured LLM outputs
- Used by Evaluator to parse `<reasoning>` and `<result>` tags

---

## Runtime Configuration

### Environment Variables (`.env` required)
- `AZURE_OPENAI_API_KEY` - Embeddings (text-embedding-3-small)
- `AZURE_OPENAI_API_KEY2` - Chat LLM (gpt-5-mini)
- `CO_API_KEY` - Cohere re-ranking
- `CEREBRAS_API_KEY` - Optional Cerebras provider
- `GEMINI_API_KEY` - Optional Gemini embeddings

### Configuration File (`config.yml`)
- `ai_platform.provider` - Switches between azure_openai/cerebras
- `azure_openai` - Deployment, endpoint, reasoning_effort
- `cerebras` - Model, max_completion_tokens
- `common` - Shared parameters (temperature, top_p, seed)

---

## Key Architectural Insights

1. **Strict separation of concerns**: Interfaces enforce clear boundaries; no implementation leakage
2. **Swappable implementations**: Any component can be replaced as long as it implements the interface
3. **Single Responsibility Principle**: Each component has exactly one reason to change
4. **Configuration over code**: AI provider switching requires zero code changes
5. **Defensive design**: Auto-creates table if missing (`datastore.py:115-120`)
6. **Rich metadata pipeline**: Page numbers, headings, and bounding boxes flow from indexing → retrieval → response
7. **Production-ready patterns**: Concurrent processing, merge-insert for idempotency, structured error handling

---

## Component Interfaces Reference

### BaseDatastore
```python
class BaseDatastore(ABC):
    @abstractmethod
    def add_items(self, items: List[DataItem]) -> None: pass

    @abstractmethod
    def get_vector(self, content: str) -> List[float]: pass

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[SearchResult]: pass
```

### BaseIndexer
```python
class BaseIndexer(ABC):
    @abstractmethod
    def index(self, document_paths: List[str]) -> List[DataItem]: pass
```

### BaseRetriever
```python
class BaseRetriever(ABC):
    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[SearchResult]: pass
```

### BaseResponseGenerator
```python
class BaseResponseGenerator(ABC):
    @abstractmethod
    def generate_response(self, query: str, search_results: List[SearchResult]) -> str: pass
```

### BaseEvaluator
```python
class BaseEvaluator(ABC):
    @abstractmethod
    def evaluate(self, query: str, response: str, expected_answer: str) -> EvaluationResult: pass
```

---

## Data Models

### DataItem
```python
class DataItem(BaseModel):
    content: str = ""
    source: str = ""
    metadata: Optional[Dict] = None
```

### SearchResult
```python
@dataclass
class SearchResult:
    content: str
    source: str
    page_no: Optional[int] = None
    headings: Optional[List[str]] = None
    bbox: Optional[Dict] = None
    relevance_score: float = 0.0
```

### EvaluationResult
```python
class EvaluationResult(BaseModel):
    question: str
    response: str
    expected_answer: str
    is_correct: bool
    reasoning: Optional[str] = None
```
