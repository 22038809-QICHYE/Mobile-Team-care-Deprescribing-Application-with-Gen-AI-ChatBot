from langchain_huggingface import HuggingFaceEmbeddings

class PubMedBERT:
    def __init__(self, model_name="NeuML/pubmedbert-base-embeddings"):
        """
        Initializes the PubMedBERT embedding model.
        """
        self.embedding_model = HuggingFaceEmbeddings(
            model_name=model_name,
            encode_kwargs={"normalize_embeddings": True}
        )

    def embed_query(self, text=None):
        """
        Embeds a single query for compatibility with RedisSemanticCache.
        
        Args:
            text (str): The user query to embed (expected by RedisSemanticCache).
            **kwargs: Additional keyword arguments (ignored for now).
        
        Returns:
            list[float]: The embedding vector for the query.
        """
        if not text or not isinstance(text, str):
            raise ValueError("The 'text' parameter must be a non-empty string.")
        return self.embedding_model.embed_query(text)

    def embed_documents(self, documents: list):
        """
        Embeds a list of document strings.
        
        Args:
            documents (list): A list of strings representing documents.
        
        Returns:
            list[list[float]]: A list of embedding vectors for the documents.
        """
        if not isinstance(documents, list) or not all(isinstance(x, str) for x in documents):
            raise ValueError("Input must be a list of strings.")
        return self.embedding_model.embed_documents(documents)
    
    def __call__(self, input):
        """
        Callable interface for embedding documents.
        """
        return self.embed_documents(input)

def test_script1():
    model = PubMedBERT()

    # Query Embedding Example
    query_embedding = model.embed_query(text="What is the latest treatment for diabetes?")
    print("Query Embedding (first 5 dimensions):\n", query_embedding[:5])

    # Document Embedding Example
    documents = [
        "This is the first document.",
        "Here is another document.",
        "This document talks about machine learning."
    ]
    document_embeddings = model.embed_documents(documents)
    print(f"Document Embedding: \n{len(document_embeddings)} entries, each of length {len(document_embeddings[0])}")




if __name__ == "__main__":
    try:
        test_script1()

    except Exception as e:
        print(f"\nAn error occurred during testing: {e}")

    finally:
        print("\nTesting complete.")
