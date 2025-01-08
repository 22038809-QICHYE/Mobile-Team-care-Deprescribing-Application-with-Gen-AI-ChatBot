import os
from dotenv import load_dotenv
from tabulate import tabulate

from langchain_community.cache import RedisSemanticCache
from langchain.globals import set_llm_cache
from langchain.schema import Generation

from Embedding_Model import PubMedBERT
from Retrieval import Retriever
from Re_ranker import CrossEncoderReRanker
from Augment import Augmentation



class RedisSemanticCacheManager:
    def __init__(self):
        """
        Initialize the CacheManager with RedisSemanticCache.
        """
        # Load environment variables from the .env file
        load_dotenv()

        # Load configuration values
        self.redis_url = os.getenv("REDIS_URL")
        self.embeddings = PubMedBERT()
        self.score_threshold = 0.7

        # Initialize RedisSemanticCache
        self.cache = RedisSemanticCache(
            redis_url=self.redis_url,
            embedding=self.embeddings,
            score_threshold=self.score_threshold
        )
        
        # Set the cache globally for LangChain compatibility
        set_llm_cache(self.cache)

    def lookup(self, query, llm_string):
        """
        Check if a semantically similar query exists in the cache.
        :param query: The input query.
        :param llm_string: The identifier for the LLM.
        :return: Cached document if found; otherwise, None.
        """
        
        try:
            cached_result = self.cache.lookup(query, llm_string)
            if cached_result:
                print(f"Cache hit for query: {query}")
                return cached_result[0].text  # Assuming the cached result is a list of Generations
            print(f"Cache miss for query: {query}")
            return None
        except Exception as e:
            print(f"\nAn error occurred during the test: {e}")


    def update(self, query, augmented_query_data, llm_string):
        """
        Update the cache with a new query-document pair.
        :param query: The input query.
        :param augmented_query_data: Dictionary containing the augmented query and context.
        :param llm_string: The identifier for the LLM.
        """
        try:
            # Extract the relevant content from the dictionary
            document = augmented_query_data.get("Content", "")
            if not document:
                print("No valid content found to update the cache.")
                return
            
            # Wrap the extracted content in a Generation object
            generation = Generation(text=document)
            self.cache.update(query, llm_string, [generation])
            print(f"Updated cache with query: {query}\nUsing {llm_string}")
            # Display the updated cache entry in tabular format
            # self.display_cached_document(query, document)
        except Exception as e:
            print(f"Error updating the cache: {e}")


    def clear_cache(self, llm_string):
        """
        Clear the entire cache globally.
        """
        try:
            self.cache.clear(llm_string = llm_string)
            print("Cache cleared globally.")
        except Exception as e:
            print(f"Error during cache clear: {e}")

    def display_cached_document(self, query, cached_document):
        """
        Display the cached document in a tabular format using tabulate.

        :param query: The input query.
        :param cached_document: The cached document content.
        """
        try:
            cached_data = [["Query", query], ["Content", cached_document]]
            formatted_cache = tabulate(cached_data, headers=["Field", "Content"], tablefmt="grid")
            print("\n=== Cached Document ===")
            print(formatted_cache)
        except Exception as e:
            print(f"Error displaying cached document: {e}")


def test_script():
    retriever = Retriever()
    reranker = CrossEncoderReRanker()
    augmentor = Augmentation()
    cache_manager = RedisSemanticCacheManager()

    user_query = "What is an example of document retrieval?"
    llm_string = "gpt-4o"

    # Cache lookup
    print("Checking cache...")
    try:
        cache_document = cache_manager.lookup(user_query, llm_string)
        if cache_document:
            print(f"Cache hit! Cached document found.")
            cache_manager.display_cached_document(user_query, cache_document)
            cache_manager.clear_cache(llm_string)
            return cache_document
    except Exception as e:
        print(f"Cache lookup error: {e}")
        return

    # If no cache hit, proceed with retrieval, re-ranking, and augmentation
    try:
        print("\nRetrieving documents...")
        retrieved_documents = retriever.retrieve_similarity_score_threshold(user_query)
        if not retrieved_documents:
            print("No documents retrieved.")
            return "No relevant documents found."

        print("\nRe-ranking documents...")
        reranked_documents = reranker.re_rank_documents(user_query, retrieved_documents)
        if not reranked_documents:
            print("Re-ranking failed.")
            return "Re-ranking failed."

        print("\nAugmenting query...")
        augmented_query_data = augmentor.augment_query_with_document(user_query, reranked_documents)
        formatted_document = augmentor.format_augmented_query(augmented_query_data)
        print(f"Augment:\n{formatted_document}\n")

        # Update the cache
        cache_manager.update(user_query, augmented_query_data, llm_string)
 
        return augmented_query_data
    except Exception as e:
        print(f"Error during testing: {e}")
        return "Process failed."



if __name__ == "__main__":
    try:
        test_script()
    except Exception as e:
        print(f"\nAn error occurred during the test: {e}")
    finally:
        print("\nTest complete.")

