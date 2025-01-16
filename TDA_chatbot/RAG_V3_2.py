from Augment import Augmentation
from Retrieval import Retriever
from Re_ranker import CrossEncoderReRanker
from Memory import RedisSemanticCacheManager

class RAGSystem:
    def __init__(self):
        """
        Initialize the RAG system with retriever, re-ranker, and cache manager.
        """
        self.retriever = Retriever()
        self.re_ranker = CrossEncoderReRanker()
        self.augmenter = Augmentation()
        self.cache_manager = RedisSemanticCacheManager()

    def process_query(self, user_query: str, llm_string: str):
        """
        Process an LLM query through retrieval, re-ranking, and caching.
        :param query: The input query.
        :return: Augmented query (with context).
        """
        # Step 1: Check cache
        cached_document = self.cache_manager.lookup(user_query, llm_string)
        if cached_document:
            print(f"Cache hit! Cached document:\n{cached_document}")
            return cached_document

        # Step 2: Retrieve documents
        
        retrieved_documents = self.retriever.retrieve_similarity_score_threshold(user_query)
        if not retrieved_documents:
            print("No documents retrieved.")
            return "No relevant documents found."
        """
        retrieved_documents = self.retriever.retrieve(user_query)
        if not retrieved_documents:
            print("No documents retrieved.")
            return "No relevant documents found."
        """
        # Step 3: Re-rank documents
        reranked_documents = self.re_ranker.re_rank_documents(user_query, retrieved_documents)
        print(reranked_documents)

        # Step 4: Augment query with top document
        augmented_query_data = self.augmenter.augment_query_with_document(user_query, reranked_documents)
        
        # Step 5: Update cache
        self.cache_manager.update(user_query, augmented_query_data, llm_string)

        return augmented_query_data

        
def test_script1():
    # Initialize RAG pipeline
    rag = RAGSystem()

    # Sample user query
    user_query = "What is the recomentdation for Rivaroxaban"

    # For caching (llm_string is a string representation of the LLM configuration)
    llm_string = "PubMedBERT"

    # Process the query through the RAG pipeline
    result = rag.process_query(user_query, llm_string)

    print(result)
    rag.cache_manager.clear_cache(llm_string)




if __name__ == "__main__":
    try:
        test_script1()

    except Exception as e:
        print(f"\nAn error occurred during testing: {e}")

    finally:
        print("\nTesting complete.")