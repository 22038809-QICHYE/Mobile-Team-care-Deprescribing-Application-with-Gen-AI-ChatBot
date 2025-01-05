from Chroma import ChromaManager
from tabulate import tabulate


class Retriever:
    def __init__(self, search_type="similarity", search_kwargs=None):
        """
        Initialize the Retriever with default settings.
        
        :param search_type: The type of search to be performed (default: "similarity").
        :param search_kwargs: Additional keyword arguments for retriever functions (default: {'k': 10}).
        :param verbose: Enable verbose logging for debugging (default: False).
        """
        self.search_type = search_type
        self.search_kwargs = search_kwargs or {'k': 10}  # Default to 10 documents
        self.chroma_client = ChromaManager().vectorstore_client

    def _get_retriever(self, search_type=None, search_kwargs=None):
        """
        Create a new retriever instance with custom or default search parameters.
        
        :param search_type: Override the search type (default: class-level search_type).
        :param search_kwargs: Override the search kwargs (default: class-level search_kwargs).
        :return: A configured retriever instance.
        """
        return self.chroma_client.as_retriever(
            search_type=search_type or self.search_type,
            search_kwargs=search_kwargs or self.search_kwargs
        )

    #=== Similarity Search ===
    def retrieve(self, query):
        """
        Perform default retrieval using the initialized search_type and search_kwargs.
        
        :param query: The query for which to retrieve documents.
        :return: A list of retrieved documents.
        """
        retriever = self._get_retriever()
        if not query.strip():
            print(f"Performing default retrieval (type: {self.search_type}, k: {self.search_kwargs['k']}) for query: {query}")
        return retriever.invoke(query)

    def retrieve_mmr(self, query):
        """
        Perform MMR (Maximum Marginal Relevance) search.
        
        :param query: The query for which to retrieve documents.
        :return: A list of retrieved documents.
        """
        retriever = self.chroma_client.as_retriever(
            search_type="mmr", 
            search_kwargs={"fetch_k": 10}  # Fetch up to 10 documents
        )
        try:
            results = retriever.invoke(query)
            if not query.strip():
                print(f"Retrieved {len(results)} documents using MMR.")
            return results
        except Exception as e:
            print(f"Error during MMR retrieval: {e}")
            return []

    def retrieve_similarity_score_threshold(self, query, score_threshold=0.5, num_documents=10):
        """
        Retrieve documents based on a minimum similarity score threshold.
        
        :param query: The query for which to retrieve documents.
        :param score_threshold: The threshold score to filter results.
        :param num_documents: The number of documents to retrieve.
        :return: A list of retrieved documents.
        """
        retriever = self._get_retriever(
            search_type='similarity_score_threshold', 
            search_kwargs={'score_threshold': score_threshold, 'k': num_documents}
        )
        try:
            results = retriever.invoke(query)
            print(f"Retrieved {len(results)} documents.")
            return results
        except Exception as e:
            print(f"Error during similarity score threshold retrieval: {e}")
            return []
        
    def retrieve_with_filter(self, query, filter_criteria, num_documents=10):
        """
        Retrieve documents using a filter based on specific criteria.
        
        :param query: The query for which to retrieve documents.
        :param filter_criteria: Dictionary containing filter conditions.
        :param num_documents: The number of documents to retrieve.
        :return: A list of retrieved documents.
        """
        retriever = self._get_retriever(
            search_kwargs={'filter': filter_criteria, 'k': num_documents}  # Explicit 'k' added
        )
        if not query.strip():
            print(f"Retrieving with filter criteria: {filter_criteria}")
        results = retriever.invoke(query)
        return results
    
    #=== Result formating ===
    def format_results(self, results):
        """
        Format the retrieved results for better readability.
        
        :param results: List of retrieved documents.
        :return: Formatted string representation of results.
        """
        if not results:
            return "No documents retrieved."

        table_data = []
        for i, doc in enumerate(results, start=1):
            content_preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
            metadata = doc.metadata
            table_data.append([i, content_preview, metadata])

        headers = ["#", "Content (Preview)", "Metadata"]
        return tabulate(table_data, headers=headers, tablefmt="grid")
    
def test_script1():
    retriever = Retriever()
    query = "What is an example of document retrieval?"

    # Test 1: Default retrieval
    print("\n--- Testing Default Retrieval ---")
    default_results = retriever.retrieve(query)
    print(retriever.format_results(default_results))

    # Test 2: MMR retrieval
    print("\n--- Testing MMR Retrieval ---")
    mmr_results = retriever.retrieve_mmr(query)
    print(retriever.format_results(mmr_results))

    # Test 3: Similarity score threshold retrieval
    print("\n--- Testing Similarity Score Threshold Retrieval ---")
    threshold_results = retriever.retrieve_similarity_score_threshold(query)
    print(retriever.format_results(threshold_results))

    # Test 4: Filtered retrieval
    filter_criteria = {'source': 'test'}
    print("\n--- Testing Filtered Retrieval ---")
    filtered_results = retriever.retrieve_with_filter(query, filter_criteria)
    print(retriever.format_results(filtered_results))



if __name__ == "__main__":    
    try:
        test_script1()

    except Exception as e:
        print(f"\nAn error occurred during testing: {e}")

    finally:
        print("\nTesting complete.")

