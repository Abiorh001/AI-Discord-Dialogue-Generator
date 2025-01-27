import logging
import os
import sys
from typing import Tuple, Union

from dotenv import load_dotenv
from llama_index.core import (
    ServiceContext,
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
    get_response_synthesizer,
)
from llama_index.core.node_parser import SentenceSplitter, SimpleNodeParser
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import BaseRetriever, VectorIndexRetriever
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.postprocessor.cohere_rerank import CohereRerank
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.retrievers.bm25 import BM25Retriever
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from qdrant_client.http.exceptions import UnexpectedResponse
from llama_parse import LlamaParse


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().handlers = []
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

# Load environment variables
load_dotenv()

Settings.llm = OpenAI(temperature=0.2, model="gpt-4-1106-preview")
Settings.embed_model = OpenAIEmbedding(model="text-embedding-ada-002")


class DegenTraderQueryEngine:
    def __init__(self):
        self.openai_api_key: Union[str, None] = os.getenv("OPENAI_API_KEY")
        self.qdrant_client = QdrantClient(host="localhost", port=6333)
        self.embed_model = OpenAIEmbedding(model="text-embedding-ada-002")
        # self.llama_cloud_api_key: Union[str, None] = os.getenv("LLAMA_CLOUD_API_KEY")
        self.cohere_api_key: Union[str, None] = os.environ.get("COHERE_API_KEY")

        self.validate_api_keys()

    def validate_api_keys(self) -> None:
        if not all(
            [
                self.openai_api_key,
                # self.llama_cloud_api_key,
                self.cohere_api_key
            ]
        ):
            raise ValueError(
                "One or more API keys are missing. List of api keys are: openai_api_key, llama_cloud_api_key, cohere_api_key"
            )

    def create_qdrant_index(self) -> VectorStoreIndex:
        collection_name = "DegenTrader-index"
        try:
            # Check if the collection exists before trying to recreate it
            self.qdrant_client.get_collection(collection_name)
            # If collection already exists, retrieve it
            vector_store = QdrantVectorStore(
                client=self.qdrant_client, collection_name=collection_name
            )
            vector_index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store, embed_model=self.embed_model
            )

        except UnexpectedResponse as e:
            if e.status_code == 404:
                print(f"Collection {collection_name} not found")
                # If collection doesn't exist, recreate it
                vector_size = 1536
                vectors_config = VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,  
                )
                self.qdrant_client.create_collection(
                    collection_name=collection_name, vectors_config=vectors_config
                )
                # Create vector store
                vector_store = QdrantVectorStore(
                    client=self.qdrant_client, collection_name=collection_name
                )
                storage_context = StorageContext.from_defaults(
                    vector_store=vector_store
                )

                # Load documents and split them into nodes
                documents = SimpleDirectoryReader(
                    "Data", recursive=True, file_extractor=None
                ).load_data()
                splitter = SentenceSplitter(chunk_size=512, chunk_overlap=20)
                nodes = splitter.get_nodes_from_documents(documents)

                # Create the vector index
                vector_index = VectorStoreIndex(
                    storage_context=storage_context,
                    embed_model=self.embed_model,
                    show_progress=True,
                    nodes=nodes,
                )
        except Exception as e:
            # Handle any errors here
            print(f"Error: {e}")
            raise e

        return vector_index


    def create_BM25_and_vector_retriever(
        self,
    ) -> Tuple[BM25Retriever, VectorIndexRetriever]:
        # load or create the pinecone vector store index
        pinecone_vector_index = self.create_pinecone_index()
        bm25_retriever = BM25Retriever.from_defaults(
            index=pinecone_vector_index, similarity_top_k=8
        )
        vector_index_retriever = VectorIndexRetriever(
            pinecone_vector_index, similarity_top_k=8
        )
        return bm25_retriever, vector_index_retriever


class HybridRetriever(BaseRetriever):
    def __init__(self, vector_index_retriever, bm25_retriever):
        self.vector_index_retriever = vector_index_retriever
        self.bm25_retriever = bm25_retriever

    def _retrieve(self, query, **kwargs):
        bm25_nodes = self.bm25_retriever.retrieve(query, **kwargs)
        vector_nodes = self.vector_index_retriever.retrieve(query, **kwargs)
        all_nodes = []
        nodes_ids = set()
        for n in bm25_nodes + vector_nodes:
            if n.node.node_id not in nodes_ids:
                all_nodes.append(n)
                nodes_ids.add(n.node.node_id)
        return all_nodes


DegenTrader_query = DegenTraderQueryEngine()
# bm25_retriever, vector_index_retriever = DegenTrader_query.create_BM25_and_vector_retriever()
# hybrid_retriever = HybridRetriever(vector_index_retriever, bm25_retriever)
vector_index = DegenTrader_query.create_qdrant_index()
vector_retriever = VectorIndexRetriever(index=vector_index, similarity_top_k=8)

cohere_rerank = CohereRerank(api_key=DegenTrader_query.cohere_api_key, top_n=8)

# configure response synthesizer
response_synthesizer = get_response_synthesizer()
similarity_postprocessor = SimilarityPostprocessor(similarity_cutoff=0.5)
degen_trader_query_engine = RetrieverQueryEngine(
    retriever=vector_retriever,
    response_synthesizer=response_synthesizer,
    node_postprocessors=[cohere_rerank],
)

# response = degen_trader_query_engine.query("which coin is good to buy based on the available market sentiment and list top 10")
# print(response)
