from Chroma import ChromaManager
from tabulate import tabulate
# MultiQuery Retrieval
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import BaseOutputParser
from langchain_core.prompts import PromptTemplate
from typing import List
# RePhraseQuery
from langchain.retrievers import RePhraseQueryRetriever
from langchain_core.output_parsers import StrOutputParser
# EnsembleRetriever
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
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
        self.chroma_client = ChromaManager()

    
    def _get_retriever(self, search_type=None, search_kwargs=None):
        """
        Create a new retriever instance with custom or default search parameters.
        
        :param search_type: Override the search type (default: class-level search_type).
        :param search_kwargs: Override the search kwargs (default: class-level search_kwargs).
        :return: A configured retriever instance.
        """
        # To switch to "Unstructured_data" collection
        # self.chroma_client.set_active_collection("Unstructured_data")

        return self.chroma_client.vectorstore_client.as_retriever(
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
        retriever = self._get_retriever(
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
    #==========================

    #=== EnsembleRetriever ===
    def retrieve_ensemble(self, query, k=10):
        try:
            # Normal Retriever
            retriever = self._get_retriever(
                search_type='similarity',
                search_kwargs={'k': k}
            )

            # Fetch stored documents using the existing function in Chroma class
            stored_docs = self.chroma_client.list_documents()

            # Convert stored_docs to a list of Document objects
            documents = [
                Document(page_content=doc["text"], metadata={"id": doc["id"], **doc.get("metadata", {})}) 
                for doc in stored_docs
            ]

            # Initialize BM25 Retriever
            bm25_retriever = BM25Retriever.from_documents(documents)
            bm25_retriever.k = k  # Number of documents to retrieve

            # Ensemble Retriever
            ensemble_retriever = EnsembleRetriever(
                retrievers=[bm25_retriever, retriever],
                weights=[0.5, 0.5]
            )   

            # Retrieve documents
            results = ensemble_retriever.invoke(query)

            print(f"Retrieved {len(results)} documents using EnsembleRetriever with MMR and BM25.")
            return results

        except Exception as e:
            print(f"Error during Ensemble retrieval: {e}")
            return []
    #=========================

    #==== Retrieval with LLM ====
    #=== MultiQuery Retrieval ===
    def retrieve_multi_query(self, query, k=5):
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
            questions based on the given user question. For a age and gender and for each medication and condition mentioned, 
            create a question that asks for recommendations. The format should be: 
            'What are the recommendations for a [age] years old [gender] [taking/with] [medication/condition]?' 
            Ensure that you cover all medications and conditions mentioned in the original question. 
            Provide these questions separated by newlines.
            Original question: {question}"""
        )
        
        # Set the prompt in the retriever
        llm_chain = prompt | llm | LineListOutputParser()

        try:
            # Initialize MultiQueryRetriever
            retriever = MultiQueryRetriever(
                retriever=self._get_retriever(
                    search_type='similarity', 
                    search_kwargs={'k': k}
                ), 
                llm_chain=llm_chain
            )
            # Invoke the retriever to get results
            results = retriever.invoke(query)
            
            # Get the generated queries
            generated_queries = llm_chain.invoke(query)
            logging.info(f"Generated queries:\n{generated_queries}")
            
            print(f"Retrieved {len(results)} documents using MultiQueryRetriever.")
            

            return results, generated_queries  # Return both documents and generated queries
        except Exception as e:
            print(f"Error during MultiQuery retrieval: {e}")
            return [], []
    #=== RePhraseQuery Retrieval ===
    def retrieve_rephrase_query(self, query, k=20):
        """
        Perform retrieval using RePhraseQueryRetriever with modern LangChain composition.
        
        :param query: The query for which to retrieve documents.
        :param k: Number of documents to retrieve (default: 20).
        :return: A list of retrieved documents.
        """
        try:
            # Initialize the language model for query rephrasing
            llm = ChatOpenAI(temperature=0)
            
            # Create a custom prompt for query rephrasing
            QUERY_PROMPT = PromptTemplate(
                input_variables=["question"],
                template="""You are an advanced AI specialized in improving search queries for better information retrieval.  
                Given the following user question, generate a more precise and alternative version of the query while preserving its meaning.  
                Ensure the rephrased query remains contextually relevant and optimized for search.  

                User Query: {question}  
                Rephrased Query:"""
            )

            # Create the query rephrasing chain
            rephrase_chain = (
                QUERY_PROMPT | llm | StrOutputParser()
            )
            
            # Generate the rephrased query
            rephrased_query = rephrase_chain.invoke({"question": query})
            
            # Create the RePhraseQueryRetriever
            rephrase_retriever = RePhraseQueryRetriever(
                retriever=self._get_retriever(
                    search_type='similarity', 
                    search_kwargs={'k': k}
                ), 
                llm_chain=rephrase_chain
            )
            
            # Invoke the retriever to get results
            results = rephrase_retriever.invoke(query)
            
            # Log and print the original and rephrased queries
            logging.info(f"Original Query: {query}")
            logging.info(f"Rephrased Query: {rephrased_query}")
            
            print("\n--- Query Rephrasing ---")
            print(f"\nOriginal Query: \n{query}")
            print(f"\nRephrased Query: \n{rephrased_query}")
            
            print(f"\nRetrieved {len(results)} documents using RePhraseQueryRetriever.")
            return results
        
        except Exception as e:
            print(f"Error during RePhraseQuery retrieval: {e}")
            return []
    #===============================

    #=== Result formating for terminal display ===    
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
            content_preview = doc.page_content[:120] + "..." if len(doc.page_content) > 100 else doc.page_content
            source = doc.metadata.get("source", "N/A")  # Extract only 'source' field from metadata
            table_data.append([i, content_preview, source])

        headers = ["#", "Content (Preview)", "Source"]
        return tabulate(table_data, headers=headers, tablefmt="grid")

#=== Testing ===
def test_script1():
    retriever = Retriever()
    query = "Age: 78, Gender: male, Medications: Digoxin (OD 0.125mg), Fluticasone (BID 2 puff), Warfarin (OD 5), Conditions: Essential hypertension (BA00), Iron deficiency anaemia (3A00), Mixed hyperlipidaemia (5C80.2)"

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
    
    # Test 5: MultiQuery retrieval
    print("\n--- Testing MultiQuery Retrieval ---")
    retrieved_docs, generated_queries = retriever.retrieve_multi_query(query)
    print(f"\nRetrieved {len(retrieved_docs)} documents:")
    print(retriever.format_results(retrieved_docs))
    # Display the generated queries
    print("\nGenerated Queries:")
    for GEN_query in generated_queries:
        print(GEN_query)
    
    # Test 6: RePhraseQuery retrieval
    print("\n--- Testing RePhraseQuery Retrieval ---")
    retrieved_docs = retriever.retrieve_rephrase_query(query)
    print(retriever.format_results(retrieved_docs))
    '''
    # Test 7: Ensemble retrieval
    print("\n--- Testing Ensemble Retrieval ---")
    ensemble_results = retriever.retrieve_ensemble(query)
    print(retriever.format_results(ensemble_results))
    

if __name__ == "__main__":    
    try:
        test_script1()

    except Exception as e:
        print(f"\nAn error occurred during testing: {e}")

    finally:
        print("\nTesting complete.")

