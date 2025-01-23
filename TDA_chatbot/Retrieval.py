from Chroma import ChromaManager
from tabulate import tabulate
# MultiQuery Retrieval
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import BaseOutputParser
from langchain_core.prompts import PromptTemplate
from typing import List
# Set logging for the queries
import logging

logging.basicConfig()
logging.getLogger("langchain.retrievers.multi_query").setLevel(logging.INFO)

# Output parser will split the LLM result into a list of queries
class LineListOutputParser(BaseOutputParser[List[str]]):
    """Output parser for a list of lines."""

    def parse(self, text: str) -> List[str]:
        lines = text.strip().split("\n")
        return list(filter(None, lines))  # Remove empty lines

class Retriever:
    def __init__(self, search_type="similarity", search_kwargs=None):
        """
        Initialize the Retriever with default settings.
        
        :param search_type: The type of search to be performed (default: "similarity").
        :param search_kwargs: Additional keyword arguments for retriever functions (default: {'k': 10}).
        :param verbose: Enable verbose logging for debugging (default: False).
        """
        self.search_type = search_type
        self.search_kwargs = search_kwargs or {'k': 20}  # Default to 20 documents
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
            search_kwargs={"k": 200, "fetch_k": 100}  # Fetch up to 10 documents
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
    
            
    #=== MultiQuery Retrieval ===
    def retrieve_multi_query(self, query, k=20):
        """
        Perform retrieval using MultiQueryRetriever and return both documents and generated queries.
        
        :param query: The query for which to retrieve documents.
        :param k: The number of documents to retrieve for each generated query.
        :return: A tuple containing a list of retrieved documents and a list of generated queries.
        """
        llm = ChatOpenAI(temperature=0)  # Initialize the LLM for query generation
        
        # Create a custom prompt to generate specific questions for each medication and condition
        prompt = PromptTemplate(
            input_variables=["question"],
            template="""You are an AI language model assistant. Your task is to generate specific 
            questions based on the given user question. For each medication and condition mentioned, 
            create a question that asks for recommendations. The format should be: 
            'What are the recommendations for [medication/condition]?' 
            Ensure that you cover all medications and conditions mentioned in the original question. 
            Provide these questions separated by newlines.
            Original question: {question}"""
        )
        
        # Set the prompt in the retriever
        llm_chain = prompt | llm | LineListOutputParser()

        try:
            # Initialize MultiQueryRetriever
            retriever = MultiQueryRetriever(
                retriever=self.chroma_client.as_retriever(), llm_chain=llm_chain
            )
            # Invoke the retriever to get results
            results = retriever.invoke(query)
            
            # Get the generated queries
            generated_queries = llm_chain.invoke(query)
            logging.info(f"Generated queries:\n{generated_queries}")
            
            print(f"Retrieved {len(results)} documents using MultiQueryRetriever.")
            
            # Limit the number of retrieved documents to k
            limited_results = results[:k]  # Only take the top k documents
            return limited_results, generated_queries  # Return both documents and generated queries
        except Exception as e:
            print(f"Error during MultiQuery retrieval: {e}")
            return [], []

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
            content_preview = doc.page_content[:60] + "..." if len(doc.page_content) > 100 else doc.page_content
            metadata= doc.metadata
            table_data.append([i, content_preview, metadata])

        headers = ["#", "Content (Preview)", "Metadata"]
        return tabulate(table_data, headers=headers, tablefmt="grid")
    
def test_script1():
    retriever = Retriever()
    query = "Age: 78, Gender: female, Medications: Ciprofloxacin (5mg diphenoxylate & 0.05mg atropine QDS), Tolterodine IR (2mg BD), Brinzolamide (1 drop TDS), Conditions: Severe diarrhoea, dementia, overactive bladder syndrome, Chronic glaucoma"
    
    '''
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
    '''

    # Test 5: MultiQuery retrieval
    print("\n--- Testing MultiQuery Retrieval ---")
    retrieved_docs, generated_queries = retriever.retrieve_multi_query(query)
    print(f"\nRetrieved {len(retrieved_docs)} documents:")
    print(retriever.format_results(retrieved_docs))
    # Display the generated queries
    print("\nGenerated Queries:")
    for query in generated_queries:
        print(query)


if __name__ == "__main__":    
    try:
        test_script1()

    except Exception as e:
        print(f"\nAn error occurred during testing: {e}")

    finally:
        print("\nTesting complete.")

