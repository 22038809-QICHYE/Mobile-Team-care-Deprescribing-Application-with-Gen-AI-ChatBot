from Retrieval import Retriever
from Re_ranker import CrossEncoderReRanker
from tabulate import tabulate

class Augmentation:
    def __init__(self):
        """Initializes the Query Augmentor."""
        pass
    

    def augment_query_with_document(self, user_query, documents):
        """
        Augments the user query with the content of all documents provided.

        :param user_query: The original user query.
        :param documents: A list of documents, each containing 'page_content'.
        :return: A dictionary with the query and combined document contexts.
        """
        if not user_query.strip():
            raise ValueError("User query is empty. Please provide a valid query.")

        #if not documents or not isinstance(documents, list):
        #    raise ValueError("Invalid documents. Ensure it is a list of documents.")

        # Extract and combine content from all documents
        combined_context = "\n\n".join(
            doc.page_content.strip() for doc in documents if hasattr(doc, "page_content")
        )

        if not combined_context:
            return {"Query": user_query.strip(), "Content": "No relevant document content available."}


        # Create the augmented query data
        augmented_query_data = {
            "Query": user_query.strip(),
            "Content": combined_context
        }

        return augmented_query_data

    def format_augmented_query(self, augmented_query_data):
        """
        Formats the augmented query using tabulate for better readability.

        :param augmented_query_data: A dictionary containing the query and context.
        :return: A formatted string representing the augmented query.
        """
        table_data = [[key, value] for key, value in augmented_query_data.items()]
        return tabulate(table_data, headers=["Field", "Content"], tablefmt="grid")


#=== Testing ===
def test_script1():
    retriever = Retriever()
    reranker = CrossEncoderReRanker()
    augmentor = Augmentation()

    user_query = "Age: 78, Gender: female, Medications: Ciprofloxacin (5mg diphenoxylate & 0.05mg atropine QDS), Tolterodine IR (2mg BD), Brinzolamide (1 drop TDS), Conditions: Severe diarrhoea, dementia, overactive bladder syndrome, Chronic glaucoma"
    
    try:
        # Retrieve documents and generated queries using the retriever
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

        # Re-rank the retrieved documents across all queries
        print("\n--- Re-ranking Documents Across Queries ---")
        reranked_documents = reranker.re_rank_documents_across_queries(generated_queries, retrieved_docs)

        # Display the re-ranked results
        print("\nRe-ranked Documents Across Queries:")
        print(reranker.format_results_multi_query(reranked_documents))

        # Augment query with top document
        augmented_query_data = augmentor.augment_query_with_document(user_query, reranked_documents)
        print(augmented_query_data)
    except ValueError as ve:
        print(f"ValueError occurred: {ve}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")




if __name__ == "__main__":
    try:
        test_script1()
    except Exception as e:
        print(f"Critical error during testing: {e}")
    finally:
        print("Testing complete.")
