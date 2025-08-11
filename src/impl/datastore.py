import os
import pyarrow as pa
from typing import List
from google import genai
from openai import AzureOpenAI
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from interface.base_datastore import BaseDatastore, DataItem

# Import LanceDB dependencies
import lancedb
from lancedb.table import Table

load_dotenv()

class Datastore(BaseDatastore):

    DB_PATH = "data/sample-lancedb"
    DB_TABLE_NAME = "rag-table"

    def __init__(self):
        self.vector_dimensions = 1536
        self.open_ai_client = AzureOpenAI(
            azure_deployment="text-embedding-3-small", 
            api_version="2024-12-01-preview", 
            api_key=os.getenv("AZURE_OPENAI_API_KEY"), 
            azure_endpoint="https://my-dna-openai.openai.azure.com/"
        )
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.vector_db = lancedb.connect(self.DB_PATH)
        self.table: Table = self._get_table()

    def reset(self) -> Table:
        # Drop the table if it exists
        try:
            self.vector_db.drop_table(self.DB_TABLE_NAME)
        except Exception as e:
            print("Unable to drop table. Assuming it doesn't exist.")

        # Create the new table.
        schema = pa.schema(
            [
                pa.field("vector", pa.list_(pa.float32(), self.vector_dimensions)),
                pa.field("content", pa.utf8()),
                pa.field("source", pa.utf8()),
            ]
        )

        self.vector_db.create_table(self.DB_TABLE_NAME, schema=schema)
        self.table = self.vector_db.open_table(self.DB_TABLE_NAME)
        print(f"✅ Table Reset/Created: {self.DB_TABLE_NAME} in {self.DB_PATH}")
        return self.table

    def get_vector(self, content: str) -> List[float]:
        response = self.open_ai_client.embeddings.create(
            input=content,
            model="text-embedding-3-small",
            dimensions=self.vector_dimensions,
        )
        embeddings = response.data[0].embedding
        return embeddings

    def get_vector_gemini(self, content: str) -> List[float]:
        response = self.gemini_client.models.embed_content(
            contents=content,
            model="gemini-embedding-001",
            config=genai.types.EmbedContentConfig(output_dimensionality=self.vector_dimensions),
        )
        [embedding_obj] = response.embeddings
        return embedding_obj.values

    def add_items(self, items: List[DataItem]) -> None:

        # Convert items to entries in parallel (since it's network bound).
        with ThreadPoolExecutor(max_workers=8) as executor:
            entries = list(executor.map(self._convert_item_to_entry, items))

        self.table.merge_insert(
            "source"
        ).when_matched_update_all().when_not_matched_insert_all().execute(entries)

    def search(self, query: str, top_k: int = 5) -> List[str]:
        vector = self.get_vector(query)
        results = (
            self.table.search(vector)
            .select(["content", "source"])
            .limit(top_k)
            .to_list()
        )

        result_content = [result.get("content") for result in results]
        return result_content

    def _get_table(self) -> Table:
        try:
            return self.vector_db.open_table(self.DB_TABLE_NAME)
        except Exception as e:
            print(f"Error opening table. Try resetting the datastore: {e}")
            return self.reset()

    def _convert_item_to_entry(self, item: DataItem) -> dict:
        """Convert a DataItem to match table schema."""
        vector = self.get_vector(item.content)
        return {
            "vector": vector,
            "content": item.content,
            "source": item.source,
        }
