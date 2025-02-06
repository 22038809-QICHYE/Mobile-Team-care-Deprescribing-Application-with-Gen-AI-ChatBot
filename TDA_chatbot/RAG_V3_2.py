from Augment import Augmentation
from Retrieval import Retriever
from Re_ranker import CrossEncoderReRanker
from Memory import ExactMatchRedisCache

class RAGSystem:
    def __init__(self):
        """
        Initialize the RAG system with retriever, re-ranker, and cache manager.
        """
        self.retriever = Retriever()
        self.re_ranker = CrossEncoderReRanker()
        self.augmenter = Augmentation()
        self.cache_manager = ExactMatchRedisCache() # exact match dont need llm_string

    # Generation engine's query(original) with original query reranking (low score short processing time)(not using)
    def process_query_normal(self, query: str, llm_string: str):
        """
        Process an LLM query through retrieval, re-ranking, and caching.
        :param query: The input query.
        :return: Augmented query (with context).
        """
        try:
            # Step 1: Check cache
            cached_document = self.cache_manager.lookup(query, llm_string)
            if cached_document:
                print(f"Cache hit! Cached document:\n{cached_document}")
                return cached_document

            # Step 2: Retrieve documents
            retrieved_documents = self.retriever.retrieve(query)
            if not retrieved_documents:
                print("No documents retrieved from the database.")
                return "No relevant documents found."
            print(self.retriever.format_results(retrieved_documents))

            # Step 3: Re-rank documents
            reranked_documents = self.re_ranker.re_rank_with_threshold(query, retrieved_documents)
            if not reranked_documents:
                print("No documents passed the re-ranking threshold.")
                return "No relevant documents found after re-ranking."
            
            # Display the re-ranked results
            print("\nRe-ranked Documents with Threshold:")
            print(self.re_ranker.format_results(reranked_documents))

            # Step 4: Augment query with top document
            augmented_query_data = self.augmenter.augment_query_with_document(query, reranked_documents)
            
            # Step 5: Update cache
            self.cache_manager.update(query, augmented_query_data, llm_string)

            return augmented_query_data
        except Exception as e:
            print(f"\nAn error occurred during testing: {e}")
    # GPT4 generated Multi query with generated query reranking (best but long processing time)
    def process_query_v2(self, query: str):
        """
        Process an LLM query through Multi query retrieval, Multi query re-ranking, and caching.
        :param query: The input query.
        :return: Augmented query (with context).
        """
        try:
            # Step 1: Check cache
            cached_document = self.cache_manager.lookup(query)
            if cached_document:
                print(f"Cache hit! Cached document:\n{cached_document}")
                return cached_document

            # Step 2: Retrieve documents and generated queries using the retriever
            print("\n--- Retrieving Documents ---")
            retrieved_docs, generated_queries = self.retriever.retrieve_multi_query(query)
            if not retrieved_docs:
                print("No documents retrieved. Cannot proceed with re-ranking.")
                return

            # Display the retrieved documents
            print(f"\nRetrieved {len(retrieved_docs)} documents:")
            print(self.retriever.format_results(retrieved_docs))

            # Display the generated queries
            print("\nGenerated Queries:")
            for GEN_query in generated_queries:
                print(GEN_query)

            # Step 3: Re-rank the retrieved documents across all queries
            print("\n--- Re-ranking Documents Across Queries ---")
            reranked_documents = self.re_ranker.re_rank_documents_across_queries(generated_queries, retrieved_docs)

            # Display the re-ranked results
            print("\nRe-ranked Documents Across Queries:")
            print(self.re_ranker.format_results_multi_query(reranked_documents))

            # Step 4: Augment query with top document
            augmented_query_data = self.augmenter.augment_query_with_document(query, reranked_documents)
            
            # Step 5: Update cache
            self.cache_manager.update(query, augmented_query_data)

            return augmented_query_data
        except Exception as e:
            print(f"\nAn error occurred during testing: {e}")
    # GPT4 generated Multi query with original query reranking (low score short processing time)
    def process_query_mix(self, query: str):
            """
            Process an LLM query through Multi query retrieval, re-ranking using original query, and caching.
            :param query: The input query.
            :return: Augmented query (with context).
            """
            try:
                # Step 1: Check cache
                cached_document = self.cache_manager.lookup(query)
                if cached_document:
                    print(f"Cache hit! Cached document:\n{cached_document}")
                    return cached_document

                # Step 2: Retrieve documents and generated queries using the retriever
                print("\n--- Retrieving Documents ---")
                retrieved_docs, generated_queries = self.retriever.retrieve_multi_query(query)
                if not retrieved_docs:
                    print("No documents retrieved. Cannot proceed with re-ranking.")
                    return

                # Display the retrieved documents
                print(f"\nRetrieved {len(retrieved_docs)} documents:")
                print(self.retriever.format_results(retrieved_docs))

                # Display the generated queries
                print("\nGenerated Queries:")
                for GEN_query in generated_queries:
                    print(GEN_query)

                # Step 3: Re-rank the retrieved documents across all queries
                print("\n--- Re-ranking Documents Origin Queries ---")
                reranked_documents = self.re_ranker.re_rank_documents(query, retrieved_docs)

                # Display the re-ranked results
                print("\nRe-ranked Documents Across Queries:")
                print(self.re_ranker.format_results(reranked_documents))

                # Step 4: Augment query with top document
                augmented_query_data = self.augmenter.augment_query_with_document(query, reranked_documents)
                
                # Step 5: Update cache
                self.cache_manager.update(query, augmented_query_data)

                return augmented_query_data
            except Exception as e:
                print(f"\nAn error occurred during testing: {e}")

#=== Testing ===
def test_normal():
    # Initialize RAG pipeline
    rag = RAGSystem()

    # Sample user query
    query = "Age: 78, Gender: female, Medications: Digoxin (OD 0.125mg), Fluticasone (BID 2 puff), Warfarin (OD 5), Conditions: Essential hypertension (BA00), Iron deficiency anaemia (3A00), Mixed hyperlipidaemia (5C80.2)"
    
    # For caching (llm_string is a string representation of the LLM configuration)
    llm_string = "gemini"

    # Process the query through the RAG pipeline
    result = rag.process_query_normal(query, llm_string)

    print(result)
    rag.cache_manager.clear_cache(llm_string)

def test_v2():
    # Initialize RAG pipeline
    rag = RAGSystem()

    # Sample user query
    query = "Age: 92, Gender: male, Medication: Metoprolol (OD 100mg), Warfarin (OD 5mg), Amiodarone (OD 800mg), Simvastatin (OD 10mg), Condition: Obesity in adults, Iron deficiency anaemia, Mixed hyperlipidaemia, Osteoporosis, Congestive heart failure, Acute myocardial infarction, Intermediate hyperglycaemia"

    #query = "Age: 78, Gender: female, Medications: Ciprofloxacin (5mg diphenoxylate & 0.05mg atropine QDS), Tolterodine IR (2mg BD), Brinzolamide (1 drop TDS), Conditions: Severe diarrhoea, dementia, overactive bladder syndrome, Chronic glaucoma"
    
    # For caching (llm_string is a string representation of the LLM configuration)
    # llm_string = "gpt-4"

    # Process the query through the RAG pipeline
    result = rag.process_query_v2(query)

    print(result)
    #`rag.cache_manager.clear_cache(llm_string)

def test_mix():
    # Initialize RAG pipeline
    rag = RAGSystem()

    # Sample user query
    #query = "Age: 78, Gender: female, Medications: Digoxin (OD 0.125mg), Fluticasone (BID 2 puff), Warfarin (OD 5), Conditions: Essential hypertension (BA00), Iron deficiency anaemia (3A00), Mixed hyperlipidaemia (5C80.2)"

    query = "Age: 92, Gender: male, Medication: Metoprolol (OD 100mg), Warfarin (OD 5mg), Amiodarone (OD 800mg), Simvastatin (OD 10mg), Condition: Obesity in adults, Iron deficiency anaemia, Mixed hyperlipidaemia, Osteoporosis, Congestive heart failure, Acute myocardial infarction, Intermediate hyperglycaemia"
    
    # For caching (llm_string is a string representation of the LLM configuration)
    #llm_string = "gpt-4"

    # Process the query through the RAG pipeline
    result = rag.process_query_mix(query)

    print(result)
    #rag.cache_manager.clear_cache(llm_string)

if __name__ == "__main__":
    try:
        test_mix()

    except Exception as e:
        print(f"\nAn error occurred during testing: {e}")

    finally:
        print("\nTesting complete.")
