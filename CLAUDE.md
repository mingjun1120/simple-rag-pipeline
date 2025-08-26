# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is a simple RAG (Retrieval Augmented Generation) pipeline built with Python that demonstrates document indexing, vector storage, retrieval, and AI-powered response generation. The architecture follows a modular design pattern with interfaces and implementations:

### Core Components

- **RAGPipeline (src/rag_pipeline.py)**: Main orchestrator that coordinates all components
- **Datastore**: Vector database operations using LanceDB with Azure OpenAI embeddings
- **Indexer**: Document processing using Docling with tiktoken tokenization (8192 max tokens per chunk)
- **Retriever**: Semantic search with Cohere re-ranking capabilities
- **ResponseGenerator**: AI response generation using configurable providers (Azure OpenAI/Cerebras)
- **Evaluator**: Response quality evaluation against expected answers

### Key Architecture Patterns

- **Interface-based design**: All components implement abstract base classes in `src/interface/`
- **Dependency injection**: Components are injected into RAGPipeline in main.py:20-27
- **Concurrent processing**: ThreadPoolExecutor used for embeddings generation and evaluation
- **Configuration-driven**: AI provider selection via config.yml (azure_openai/cerebras)

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Core Pipeline Commands
```bash
# Full pipeline: reset + index + evaluate
python main.py run

# Reset vector database
python main.py reset

# Index documents from directory
python main.py add -p "sample_data/source/"

# Query the system
python main.py query "Your question here"

# Evaluate against test questions
python main.py evaluate -f "sample_data/eval/sample_questions.json"
```

## Configuration

### Environment Variables (.env required)
```bash
AZURE_OPENAI_API_KEY="<embeddings_key>"
AZURE_OPENAI_API_KEY2="<llm_key>" 
CO_API_KEY="<cohere_reranking_key>"
CEREBRAS_API_KEY="<optional_cerebras_key>"
GEMINI_API_KEY="<optional_gemini_key>"
```

### AI Provider Configuration (config.yml)
- Switch between `azure_openai` and `cerebras` providers
- Configure model parameters (temperature, top_p, seed, reasoning_effort)
- Azure OpenAI uses GPT-5 Mini with reasoning effort
- Cerebras uses gpt-oss-120b model

## Key Implementation Details

### Vector Storage
- **Database**: LanceDB at `data/sample-lancedb/rag-table`
- **Embeddings**: Azure OpenAI text-embedding-3-small (1536 dimensions)
- **Schema**: vector, content, source fields with merge_insert operations

### Document Processing
- **Chunking**: HybridChunker with OpenAI tokenizer (8192 max tokens)
- **Format**: PDF processing via Docling with heading preservation
- **Metadata**: Source tracking as `filename:chunk_index`

### Retrieval Strategy
- **Initial retrieval**: Vector similarity search (configurable top_k, default 3)
- **Re-ranking**: Cohere API for improved relevance
- **Context formatting**: Headings + content for better LLM understanding

## File Structure Significance

- `src/interface/`: Abstract base classes defining component contracts
- `src/impl/`: Concrete implementations of all components
- `src/util/`: Utility functions (AI invocation, XML extraction)
- `sample_data/`: Test data with PDFs and evaluation questions
- `data/`: LanceDB vector database storage location

## Testing and Evaluation

The system includes built-in evaluation capabilities:
- Evaluation questions in `sample_data/eval/sample_questions.json`
- Concurrent evaluation processing (10 max workers)
- AI-based correctness evaluation with reasoning explanations
- Score reporting with detailed question-by-question analysis

## Plan & Review

### Before starting work
- Always in plan mode and think harder to make a plan
- After get the plan, make sure you write the plan to .claude/tasks/TASK_NAME.md.
- The plan should be a detailed implementation plan and the reasoning behind them, as well as tasks broken down.
- If the task require external knowledge or certain package, also research to get latest knowledge (Use Task tool for research)
- Don't over plan it, always think MVP.
- Once you write the plan, firstly ask me to review it. Do not continue until I approve the plan.

### While implementing
- You should update the plan as you work.
- After you complete tasks in the plan, you should update and append detailed descriptions of the changes you made, so following tasks can be easily hand over to other engineers.