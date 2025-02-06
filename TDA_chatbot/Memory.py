import os
from dotenv import load_dotenv
from tabulate import tabulate
# Semantic similarity-based cache
from langchain_community.cache import RedisSemanticCache
from langchain.globals import set_llm_cache
from langchain.schema import Generation
from Embedding_Model import PubMedBERT
# Key-Value Store
import redis
import json

from Retrieval import Retriever
from Re_ranker import CrossEncoderReRanker
from Augment import Augmentation


# Semantic similarity-based cache
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
        self.score_threshold = 1

        # Initialize RedisSemanticCache
        self.cache = RedisSemanticCache(
            redis_url=self.redis_url,
            embedding=self.embeddings,
            score_threshold=self.score_threshold
        )
        
        # Set the cache globally for LangChain compatibility
        # set_llm_cache(self.cache)

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
                for cached_prompt in cached_result:
                    cached_prompt.text == query
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

def test_script1():
    retriever = Retriever() 
    reranker = CrossEncoderReRanker()
    augmentor = Augmentation()
    cache_manager = RedisSemanticCacheManager()

    user_query = "Age: 78, Gender: male, Medications: Digoxin (OD 0.125mg), Fluticasone (BID 2 puff), Warfarin (OD 5), Conditions: Essential hypertension (BA00), Iron deficiency anaemia (3A00), Mixed hyperlipidaemia (5C80.2)"

    llm_string = "gpt-4"

    try:
        # Step 1: Check cache
        cached_document = cache_manager.lookup(user_query, llm_string)
        if cached_document:
            print(f"Cache hit! Cached document:\n{cached_document}")
            return cached_document

        # Step 2: Retrieve documents and generated queries using the retriever
        print("\n--- Retrieving Documents ---")
        retrieved_docs, generated_queries = retriever.retrieve_multi_query(user_query)
        if not retrieved_docs:
            print("No documents retrieved. Cannot proceed with re-ranking.")
            return

        # Display the retrieved documents
        print(f"\nRetrieved {len(retrieved_docs)} documents:")
        print(retriever.format_results(retrieved_docs))

        # Display the generated queries
        print("\nGenerated Queries:")
        for GEN_query in generated_queries:
            print(GEN_query)

        # Step 3: Re-rank the retrieved documents across all queries
        print("\n--- Re-ranking Documents Across Queries ---")
        reranked_documents = reranker.re_rank_documents_across_queries(generated_queries, retrieved_docs)

        # Display the re-ranked results
        print("\nRe-ranked Documents Across Queries:")
        print(reranker.format_results_multi_query(reranked_documents))

        # Step 4: Augment query with top document
        augmented_query_data = augmentor.augment_query_with_document(user_query, reranked_documents)
                
        # Step 5: Update cache
        cache_manager.update(user_query, augmented_query_data, llm_string)
    
        return augmented_query_data
    
    except Exception as e:
        print(f"Error during testing: {e}")
        return "Process failed."


# Key-Value Store cache
class ExactMatchRedisCache:
    def __init__(self):
        load_dotenv()
        self.redis_url = os.getenv("REDIS_URL")
        self.redis_client = redis.Redis.from_url(self.redis_url, decode_responses=True)

    def lookup(self, query):
        """Retrieve the exact cached document if available."""
        cached_result = self.redis_client.get(query.strip().lower())  # Normalize for consistency
        if cached_result:
            print(f"Cache hit for query: {query}")
            return cached_result
        print(f"Cache miss for query: {query}")
        return None

    def update(self, query, document, ttl=3600):  # Default TTL = 1 hour
        """Store query and document pair in cache with TTL."""
        if isinstance(document, dict):  
            document_content = document.get("Content", "").strip()
        else:
            document_content = str(document).strip()  # Ensure it's a string

        if document_content:  # Ensure it's not empty
            cache_entry = json.dumps({"query": query.strip(), "document": document_content})  # Convert to JSON
            self.redis_client.setex(query.strip().lower(), ttl, cache_entry)  # Store with TTL
            print(f"Updated cache with exact query match: {query} (Expires in {ttl} seconds)")
        else:
            print("No valid content found to update the cache.")

    def clear_cache(self):
        """Clear the entire cache."""
        self.redis_client.flushdb()
        print("Cache cleared.")

def test_script2():
    retriever = Retriever() 
    reranker = CrossEncoderReRanker()
    augmentor = Augmentation()
    cache_manager = ExactMatchRedisCache()

    query = "Age: 78, Gender: female, Medications: Digoxin (OD 0.125mg), Fluticasone (BID 2 puff), Warfarin (OD 5), Conditions: Essential hypertension (BA00), Iron deficiency anaemia (3A00), Mixed hyperlipidaemia (5C80.2)"
    
    try:
        # Step 1: Check cache
        cached_document = cache_manager.lookup(query)
        if cached_document:
            print(f"Cache hit! Cached document:\n{cached_document}")
            return cached_document

        # Step 2: Retrieve documents and generated queries using the retriever
        print("\n--- Retrieving Documents ---")
        retrieved_docs, generated_queries = retriever.retrieve_multi_query(query)
        if not retrieved_docs:
            print("No documents retrieved. Cannot proceed with re-ranking.")
            return

        # Display the retrieved documents
        print(f"\nRetrieved {len(retrieved_docs)} documents:")
        print(retriever.format_results(retrieved_docs))

        # Display the generated queries
        print("\nGenerated Queries:")
        for GEN_query in generated_queries:
            print(GEN_query)

        # Step 3: Re-rank the retrieved documents across all queries
        print("\n--- Re-ranking Documents Across Queries ---")
        reranked_documents = reranker.re_rank_documents_across_queries(generated_queries, retrieved_docs)

        # Display the re-ranked results
        print("\nRe-ranked Documents Across Queries:")
        print(reranker.format_results_multi_query(reranked_documents))

        # Step 4: Augment query with top document
        augmented_query_data = augmentor.augment_query_with_document(query, reranked_documents)
            
        # Step 5: Update cache
        cache_manager.update(query, augmented_query_data)
 
        return augmented_query_data
    except Exception as e:
        print(f"Error during testing: {e}")
        return "Process failed."


if __name__ == "__main__":
    try:
        test_script2()
    except Exception as e:
        print(f"\nAn error occurred during the test: {e}")
    finally:
        print("\nTest complete.")

