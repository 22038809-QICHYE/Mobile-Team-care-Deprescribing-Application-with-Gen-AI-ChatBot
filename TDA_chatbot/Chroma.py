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
        self.collection_name = os.getenv("COLLECTION_NAME")

        if not self.chroma_path or not self.collection_name:
            raise ValueError("CHROMA_PATH and COLLECTION_NAME must be set in the .env file.")

        # Initialize the embedding function
        self.embedding_function = PubMedBERT()

        # Initialize the ChromaDB client for collection management
        self.client = chromadb.PersistentClient(path=self.chroma_path)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name, 
            embedding_function=self.embedding_function
        )

        # Initialize the Chroma client for document management
        self.vectorstore_client = Chroma(
            client=self.client,
            collection_name=self.collection_name,
            embedding_function=self.embedding_function
        )


    #=== COLLECTIONS ===
    def list_collections(self):
        """
        List all available collections in ChromaDB.
        
        :return: List of collection names.
        """
        return [collection.name for collection in self.client.list_collections()]
        
    def switch_collection(self, new_collection_name):
        """
        Switch to a different collection.

        :param new_collection_name: Name of the collection to switch to.
        """
        self.collection_name = new_collection_name
        self.collection = self.client.get_or_create_collection(name=new_collection_name)
        print(f"Switched to collection: {self.collection_name}")

    def delete_collection(self, collection_name):
        """
        Delete a collection.

        :param collection_name: Name of the collection to delete.
        """
        self.client.delete_collection(name=collection_name)
        print(f"Deleted collection: {collection_name}")


    #=== DOCUMENTS ===
    def list_documents(self):
        """
        List all documents in the current collection.

        :return: List of documents with their IDs and metadata.
        """
        if not self.collection:
            raise ValueError("Collection is not initialized.")
        
        # Fetch all documents in the collection
        documents = self.collection.get()
        
        # Check if the collection has any documents
        if not documents or not documents.get("documents"):
            print("No documents found in the collection.")
            return None

        # Format the documents
        doc_list = [
            {
                "id": doc_id,
                "text": doc_text,
                "metadata": metadata
            }
            for doc_id, doc_text, metadata in zip(
                documents["ids"], 
                documents["documents"], 
                documents["metadatas"]
            )
        ]
        
        return doc_list

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
        
        # Add the documents to the vectorstore
        self.vectorstore_client.add_documents(document_objects)

        """
        # Synchronize collection in ChromaDB
        for doc in documents:
            self.collection.add(
                ids=[doc["id"]],
                documents=[doc["text"]],
                metadatas=[doc.get("metadata", {})]
            )
        """

    def delete_document(self, document_id):
        """
        Delete a specific document by ID.

        :param document_id: ID of the document to delete.
        """
        if not self.collection:
            raise ValueError("Collection is not initialized.")

        # Fetch document to check if it exists
        existing_docs = self.collection.get(ids=[document_id])
        if not existing_docs["ids"] or not existing_docs["ids"][0]:
            print(f"Document with ID '{document_id}' does not exist in the collection.")
            return

        # Proceed with deletion
        self.collection.delete(ids=[document_id])
        print(f"Deleted document with ID: {document_id}")
    
    def delete_document_via_metadata(self, metadata_id):
        """
        Delete a specific document by its metadata 'id'.

        :param metadata_id: Metadata 'id' of the document to delete.
        """
        if not self.collection:
            raise ValueError("Collection is not initialized.")

        # Fetch all documents in the collection
        documents = self.collection.get()

        # Check if documents exist
        if not documents or not documents.get("documents"):
            print(f"No documents found in the collection.")
            return

        # Search for the document with the specified metadata 'id'
        for doc_id, doc_metadata in zip(documents["ids"], documents["metadatas"]):
            if doc_metadata.get("id") == metadata_id:
                # Delete the document by its Chroma ID
                self.collection.delete(ids=[doc_id])
                print(f"Deleted document with metadata ID: {metadata_id}")
                return

        print(f"Document with metadata ID '{metadata_id}' not found.")

    def delete_documents_by_metadata_source(self, source_value):
        """
        Delete all documents that match the specified metadata 'source'.

        :param source_value: The value of the 'source' metadata to match for deletion.
        """
        if not self.collection:
            raise ValueError("Collection is not initialized.")

        # Fetch all documents in the collection
        documents = self.collection.get()

        # Check if documents exist
        if not documents or not documents.get("documents"):
            print("No documents found in the collection.")
            return

        # List to store IDs of documents to delete
        ids_to_delete = []

        # Search for documents with the specified metadata 'source'
        for doc_id, doc_metadata in zip(documents["ids"], documents["metadatas"]):
            if doc_metadata.get("source") == source_value:
                ids_to_delete.append(doc_id)

        # Delete the documents by their IDs
        if ids_to_delete:
            self.collection.delete(ids=ids_to_delete)
            print(f"Deleted documents with source '{source_value}': {ids_to_delete}")
        else:
            print(f"No documents found with source '{source_value}'.")


def test_script1():
        # Initialize ChromaManager
        print("\nInitializing ChromaManager...")
        manager = ChromaManager()
        print("ChromaManager initialized successfully.")
        
        # List available collections
        print("\nListing available collections...")
        collections = manager.list_collections()
        print(f"Available collections: {collections}")
        '''
        # Test add_documents
        sample_documents = [
            {"id": "doc1", "text": "This is a sample document.", "metadata": {"source": "test"}},
            {"id": "doc2", "text": "Another example of a document.", "metadata": {"source": "test"}}
        ]
        print("\nAdding documents...")
        manager.add_documents(sample_documents)
        print("Documents added successfully.")
        '''
        # Test list_documents
        print("\nListing all documents in the collection...")
        documents = manager.list_documents()
        if documents:
            print("Documents in collection:")
            for doc in documents:
                print(f"ID: {doc['id']}, Text: {doc['text']}, Metadata: {doc['metadata']}")
        else:
            print("No documents found in the collection.")

        '''
        # Test deleting a document
        doc_id_to_delete = "5ed81d86-a7a9-413a-8aed-c36024326a67"
        print(f"\nDeleting document with ID: '{doc_id_to_delete}'...")
        manager.delete_document(document_id=doc_id_to_delete)
        
        # Test list_documents
        print("\nListing all documents in the collection...")
        documents = manager.list_documents()
        if documents:
            print("Documents in collection:")
            for doc in documents:
                print(f"ID: {doc['id']}, Text: {doc['text']}, Metadata: {doc['metadata']}")
        else:
            print("No documents found in the collection.")
        
        # Test switching collections
        new_collection_name = "Unstructured_data"
        print(f"\nSwitching to new collection: '{new_collection_name}'...")
        manager.switch_collection(new_collection_name=new_collection_name)
        
        # Test deleting the collection
        print(f"\nDeleting collection: '{new_collection_name}'...")
        manager.delete_collection(collection_name=new_collection_name)
        print(f"Collection '{new_collection_name}' deleted successfully.")
       
        '''
        # Test deleting a document via source
        doc_id_to_delete = "C://VS_CODES//RAG//Upload\\Table 6.csv"
        print(f"\nDeleting document with ID: '{doc_id_to_delete}'...")
        manager.delete_documents_by_metadata_source(doc_id_to_delete)
        

def test_script2():
        # Initialize ChromaManager
        print("\nInitializing ChromaManager...")
        manager = ChromaManager()
        print("ChromaManager initialized successfully.")
        """
        # List available collections
        print("\nListing available collections...")
        collections = manager.list_collections()
        print(f"Available collections: {collections}")

        # Test add_documents
        sample_documents = [
            {"id": "doc1", "text": "This is a sample document.", "metadata": {"source": "test"}},
            {"id": "doc2", "text": "Another example of a document.", "metadata": {"source": "test"}}
        ]
        print("\nAdding documents...")
        manager.add_documents(sample_documents)
        print("Documents added successfully.")
        
        # Test list_documents
        print("\nListing all documents in the collection...")
        documents = manager.list_documents()
        if documents:
            print("Documents in collection:")
            for doc in documents:
                print(f"ID: {doc['id']}, Text: {doc['text']}, Metadata: {doc['metadata']}")
        else:
            print("No documents found in the collection.")
        """
        # Test deleting a document by metadata ID
        metadata_id_to_delete = "csv_131"
        print(f"\nDeleting document with metadata ID: '{metadata_id_to_delete}'...")
        manager.delete_document_via_metadata(metadata_id=metadata_id_to_delete)

        # Test list_documents
        print("\nListing all documents in the collection...")
        documents = manager.list_documents()
        if documents:
            print("Documents in collection:")
            for doc in documents:
                print(f"ID: {doc['id']}, Text: {doc['text']}, Metadata: {doc['metadata']}")
        else:
            print("No documents found in the collection.")
        """
        # Test switching collections
        new_collection_name = "new_test_collection"
        print(f"\nSwitching to new collection: '{new_collection_name}'...")
        manager.switch_collection(new_collection_name=new_collection_name)

        # Test deleting the collection
        print(f"\nDeleting collection: '{new_collection_name}'...")
        manager.delete_collection(collection_name=new_collection_name)
        print(f"Collection '{new_collection_name}' deleted successfully.")
        """


if __name__ == "__main__":
    try:
        test_script1()

    except Exception as e:
        print(f"\nAn error occurred during testing: {e}")

    finally:
        print("\nTesting complete.")
