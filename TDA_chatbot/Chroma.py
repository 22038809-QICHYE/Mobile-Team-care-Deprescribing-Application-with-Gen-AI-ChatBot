import os
import chromadb
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from Embedding_Model import PubMedBERT


class ChromaManager:
    def __init__(self):
        # Load environment variables from the .env file
        load_dotenv()

        # Load configuration values
        self.chroma_path = os.getenv("CHROMA_PATH")
        self.collection_name_s = os.getenv("COLLECTION_NAME_S")  # Structured_data
        self.collection_name_u = os.getenv("COLLECTION_NAME_U")  # Unstructured_data

        if not self.chroma_path or not self.collection_name_s or not self.collection_name_u:
            raise ValueError("CHROMA_PATH, COLLECTION_NAME_S, and COLLECTION_NAME_U must be set in the .env file.")

        # Initialize the embedding function
        self.embedding_function = PubMedBERT()

        # Initialize the ChromaDB client
        self.client = chromadb.PersistentClient(path=self.chroma_path)

        # Initialize both collections
        self.collections = {
            "Structured_data": self.client.get_or_create_collection(
                name=self.collection_name_s,
                embedding_function=self.embedding_function
            ),
            "Unstructured_data": self.client.get_or_create_collection(
                name=self.collection_name_u,
                embedding_function=self.embedding_function    
            )
        }

        # Set the default collection
        self.active_collection = self.collection_name_s

        # Initialize LangChain Chroma wrapper for retrieval
        self.vectorstore_client = Chroma(
            client=self.client,
            collection_name=self.collection_name_s,
            embedding_function=self.embedding_function
        )


    # === COLLECTIONS ===
    def set_active_collection(self, collection_name: str):
        """
        Switch between Structured_data and Unstructured_data collections.

        :param collection_name: Name of the collection to use.
        """
        if collection_name not in self.collections:
            raise ValueError(f"Invalid collection name. Choose from: {list(self.collections.keys())}")

        self.active_collection = collection_name
        self.vectorstore_client = Chroma(
            client=self.client,
            collection_name=self.collections[collection_name].name,
            embedding_function=self.embedding_function
        )

    def get_current_collection(self):
        """Return the name of the currently active collection."""
        return self.active_collection
    
    def list_collections(self):
        """
        List all available collections in ChromaDB.

        :return: List of collection names.
        """
        try:
            return self.client.list_collections()  # Directly returns a list of collection names in v0.6.0+
        except Exception as e:
            print(f"Error listing collections: {e}")
            return []

    def delete_collection(self, collection_name: str):
        """
        Delete a collection.

        :param collection_name: Name of the collection to delete.
        """
        if collection_name in self.collections:
            self.client.delete_collection(name=self.collections[collection_name].name)
            del self.collections[collection_name]
            print(f"Deleted collection: {collection_name}")
        else:
            print(f"Collection '{collection_name}' not found.")

    # === DOCUMENTS ===
    def list_documents(self):
        """
        List all documents in the current collection.

        :return: List of documents with their IDs, text, and metadata.
        """
        collection = self.collections[self.active_collection]
        documents = collection.get()

        if not documents or not documents.get("documents"):
            print("No documents found in the collection.")
            return None

        return [
            {"id": doc_id, "text": doc_text, "metadata": metadata}
            for doc_id, doc_text, metadata in zip(
                documents["ids"], documents["documents"], documents["metadatas"]
            )
        ]

    def add_documents(self, documents):
        """
        Add documents to the Chroma vector store.

        :param documents: List of dictionaries with 'id', 'text', and optional 'metadata'.
        """
        if not isinstance(documents, list):
            raise ValueError("Documents should be a list of dictionaries with 'id', 'text', and 'metadata'.")

        # Convert dictionaries to Document objects
        document_objects = [
            Document(page_content=doc["text"], metadata={"id": doc["id"], **doc.get("metadata", {})})
            for doc in documents
        ]

        # Add the documents to the active vector store
        self.vectorstore_client.add_documents(document_objects)

    def delete_document(self, document_id):
        """
        Delete a specific document by ID in a active collection.

        :param document_id: ID of the document to delete.
        """
        collection = self.collections[self.active_collection]

        existing_docs = collection.get(ids=[document_id])
        if not existing_docs["ids"]:
            print(f"Document with ID '{document_id}' does not exist in the collection.")
            return

        collection.delete(ids=[document_id])
        print(f"Deleted document with ID: {document_id}")

    def delete_document_via_metadata(self, metadata_id):
        """
        Delete a specific document by its metadata 'id'.

        :param metadata_id: Metadata 'id' of the document to delete.
        """
        collection = self.collections[self.active_collection]
        documents = collection.get()

        if not documents or not documents.get("documents"):
            print("No documents found in the collection.")
            return

        for doc_id, doc_metadata in zip(documents["ids"], documents["metadatas"]):
            if doc_metadata.get("id") == metadata_id:
                collection.delete(ids=[doc_id])
                print(f"Deleted document with metadata ID: {metadata_id}")
                return

        print(f"Document with metadata ID '{metadata_id}' not found.")

    def delete_documents_by_metadata_source(self, source_value):
        """
        Delete all documents that match the specified metadata 'source'.

        :param source_value: The value of the 'source' metadata to match for deletion.
        """
        collection = self.collections[self.active_collection]
        documents = collection.get()

        if not documents or not documents.get("documents"):
            print("No documents found in the collection.")
            return

        ids_to_delete = [doc_id for doc_id, doc_metadata in zip(documents["ids"], documents["metadatas"]) 
        if doc_metadata.get("source") == source_value]

        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            print(f"Deleted documents with source '{source_value}': {ids_to_delete}")
        else:
            print(f"No documents found with source '{source_value}'.")


def test_collection_add_doc():
    # Initialize Chroma Manager
    chroma_manager = ChromaManager()

    # === Test Structured_data Collection ===
    print("\n--- Testing Structured_data Collection ---")

    # Getting name of current collection
    current_collection=chroma_manager.get_current_collection()
    print(f"Currently using {current_collection} collection.")

    # Add a document to Structured_data
    structured_doc = [
        {"id": "structured_1", "text": "This is the first structured data document for testing.", "metadata": {"source": "test_structured"}},
        {"id": "structured_2", "text": "This is the second structured data document for testing.", "metadata": {"source": "test_structured"}}
    ]
    chroma_manager.add_documents(structured_doc)
    print("Document added to Structured_data.")

    # List all documents in Structured_data
    structured_docs = chroma_manager.list_documents()
    print("Documents in Structured_data:", structured_docs)


    # === Test Unstructured_data Collection ===
    print("\n--- Testing Unstructured_data Collection ---")

    # Switch to Unstructured_data collection
    chroma_manager.set_active_collection("Unstructured_data")

    # Getting name of current collection
    current_collection=chroma_manager.get_current_collection()
    print(f"Currently using {current_collection} collection.")

    # Add a document to Unstructured_data
    unstructured_doc = [
        {"id": "unstructured_1", "text": "This is the first unstructured data document for testing.", "metadata": {"source": "test_unstructured"}},
        {"id": "unstructured_2", "text": "This is the second unstructured data document for testing.", "metadata": {"source": "test_unstructured"}}
    ]
    chroma_manager.add_documents(unstructured_doc)
    print("Document added to Unstructured_data.")

    # List all documents in Unstructured_data
    unstructured_docs = chroma_manager.list_documents()
    print("Documents in Unstructured_data:", unstructured_docs)

    # Test listing collections
    print("\nListing available collections...")
    collections = chroma_manager.list_collections()
    print(f"Available collections: {collections}")

def test_collection_del_doc():
    # Initialize Chroma Manager
    chroma_manager = ChromaManager()

    # === Test Structured_data Collection ===
    print("\n--- Testing Structured_data Collection ---")

    # Getting name of current collection
    current_collection=chroma_manager.get_current_collection()
    print(f"\nCurrently using {current_collection} collection.")

    # Test deleting documents by metadata source
    # metadata_source = "C://VS_CODES//RAG//Upload\\Table 6.csv"
    metadata_source = "test_structured"
    print(f"\nDeleting documents with source '{metadata_source}'...")
    chroma_manager.delete_documents_by_metadata_source(metadata_source)

    # List all documents in Structured_data
    structured_docs = chroma_manager.list_documents()
    print("\nDocuments in Structured_data:", structured_docs)


    # === Test Unstructured_data Collection ===
    print("\n--- Testing Unstructured_data Collection ---")

    # Switch to Unstructured_data collection
    chroma_manager.set_active_collection("Unstructured_data")
    
    # Getting name of current collection
    current_collection=chroma_manager.get_current_collection()
    print(f"\nCurrently using {current_collection} collection.")

    # Test deleting documents by metadata source
    # metadata_source = "C://VS_CODES//RAG//Upload\\BEERS J American Geriatrics Society - 2023 -  - American Geriatrics Society 2023 updated AGS Beers Criteria  for potentially.pdf"
    metadata_source = "test_unstructured"
    print(f"\nDeleting documents with source '{metadata_source}'...")
    chroma_manager.delete_documents_by_metadata_source(metadata_source)

    # List all documents in Unstructured_data
    unstructured_docs = chroma_manager.list_documents()
    print("Documents in Unstructured_data:", unstructured_docs)

    # Test listing collections
    print("\nListing available collections...")
    collections = chroma_manager.list_collections()
    print(f"Available collections: {collections}")

def hy_app_test():
    # Initialize Chroma Manager
    chroma_manager = ChromaManager()

    # === Test Structured_data Collection ===
    print("\n--- Testing Structured_data Collection ---")

    # Getting name of current collection
    current_collection=chroma_manager.get_current_collection()
    print(f"Currently using {current_collection} collection.")

    # List all documents in Structured_data
    structured_docs = chroma_manager.list_documents()
    print("Documents in Structured_data:", structured_docs)
    
    """
    # === Test Unstructured_data Collection ===
    print("\n--- Testing Unstructured_data Collection ---")

    # Switch to Unstructured_data collection
    chroma_manager.set_active_collection("Unstructured_data")

    # Getting name of current collection
    current_collection=chroma_manager.get_current_collection()
    print(f"Currently using {current_collection} collection.")

    # List all documents in Unstructured_data
    unstructured_docs = chroma_manager.list_documents()
    print("Documents in Unstructured_data:", unstructured_docs)

    # Test listing collections
    print("\nListing available collections...")
    collections = chroma_manager.list_collections()
    print(f"Available collections: {collections}")
    """
    
if __name__ == "__main__":
    try:
        hy_app_test()

    except Exception as e:
        print(f"\nAn error occurred during testing: {e}")

    finally:
        print("\nTesting complete.")
