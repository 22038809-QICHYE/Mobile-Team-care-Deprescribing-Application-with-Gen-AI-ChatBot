from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from Retrieval import Retriever
from tabulate import tabulate


class CrossEncoderReRanker:
    def __init__(self, model_name="ncbi/MedCPT-Cross-Encoder"):
        """
        Initializes the CrossEncoder ReRanker with the specified model.
        :param model_name: Name of the HuggingFace model to be used.
        """
        self.cross_encoder = HuggingFaceCrossEncoder(model_name=model_name)

    def re_rank_documents(self, query_text, retrieved_docs, top_k=10):
        """
        Re-rank retrieved documents using a Cross-Encoder.

        :param query_text: The query string provided by the user.
        :param retrieved_docs: A list of documents retrieved by the retriever.
        :param top_k: The number of top documents to return after re-ranking.
        :return: A list of re-ranked documents with their scores.
        """
        if not retrieved_docs:
            print("No documents retrieved for re-ranking.")
            return []

        try:
            # Prepare input pairs for the Cross-Encoder
            query_doc_pairs = [(query_text, doc.page_content) for doc in retrieved_docs]

            # Score the pairs using the Cross-Encoder
            scores = self.cross_encoder.score(query_doc_pairs)

            # Attach scores to documents and sort them
            for i, doc in enumerate(retrieved_docs):
                doc.metadata["score"] = scores[i]  # Store score in the document's metadata

            re_ranked_docs = sorted(retrieved_docs, key=lambda d: d.metadata["score"], reverse=True)

            # Return top-k documents
            return re_ranked_docs[:top_k]

        except Exception as e:
            print(f"Error during re-ranking: {e}")
            return []

    def re_rank_with_threshold(self, query_text, retrieved_docs, score_threshold=0.5):
        """
        Re-rank retrieved documents and filter by a score threshold.

        :param query_text: The query string provided by the user.
        :param retrieved_docs: A list of documents retrieved by the retriever.
        :param score_threshold: Minimum score a document must have to be included in the results.
        :return: A list of documents that meet or exceed the score threshold.
        """
        if not retrieved_docs or retrieved_docs == []:
            print("No documents retrieved for re-ranking.")
            return "No relevant documents found."

        try:
            # Prepare input pairs for the Cross-Encoder
            query_doc_pairs = [(query_text, doc.page_content) for doc in retrieved_docs]

            # Score the pairs using the Cross-Encoder
            scores = self.cross_encoder.score(query_doc_pairs)

            # Attach scores to documents and filter by threshold
            for i, doc in enumerate(retrieved_docs):
                doc.metadata["score"] = scores[i]  # Store score in the document's metadata

            filtered_docs = [doc for doc in retrieved_docs if doc.metadata["score"] >= score_threshold]

            # Sort the filtered documents by score in descending order
            filtered_docs.sort(key=lambda d: d.metadata["score"], reverse=True)

            return filtered_docs

        except Exception as e:
            print(f"Error during threshold-based re-ranking: {e}")
            return []

    # only for retrieve_multi_query function from Retrieval.py file
    def re_rank_documents_across_queries(self, queries, retrieved_docs, score_threshold=0.8):
        """
        Re-rank retrieved documents using a Cross-Encoder across multiple queries.

        :param queries: A list of query strings generated from the user's input.
        :param retrieved_docs: A list of documents retrieved by the retriever.
        :return: A list of re-ranked documents with their aggregated scores.
        """
        if not retrieved_docs:
            print("No documents retrieved for re-ranking.")
            return []

        try:
            # Initialize a score map to aggregate scores for each document
            score_map = {doc.id: 0 for doc in retrieved_docs}  # Assuming each document has a unique 'id'

            # Score each document for each query
            for query in queries:
                query_doc_pairs = [(query, doc.page_content) for doc in retrieved_docs]
                scores = self.cross_encoder.score(query_doc_pairs)

                # Aggregate scores for each document
                for i, doc in enumerate(retrieved_docs):
                    score_map[doc.id] += scores[i]  # Sum scores for the same document

            # Update documents with aggregated scores
            for doc in retrieved_docs:
                doc.metadata["score"] = score_map.get(doc.id, 0)

            # Filter documents by score threshold
            filtered_docs = [doc for doc in retrieved_docs if doc.metadata["score"] >= score_threshold]


            # Sort documents by aggregated scores
            re_ranked_docs = sorted(filtered_docs, key=lambda d: d.metadata.get("score", 0), reverse=True)

            return re_ranked_docs

        except Exception as e:
            print(f"Error during re-ranking: {e}")
            return []
    # only for re_rank_documents_across_queries function
    def format_results_multi_query(self, re_ranked_docs):
        """
        Format the re-ranked documents for better readability.

        :param re_ranked_docs: List of re-ranked documents with scores.
        :return: A formatted string representation of the results.
        """
        table_data = [
            [i + 1, doc.page_content[:100] + "...", round(doc.metadata.get("score", 0), 4)]
            for i, doc in enumerate(re_ranked_docs)
        ]

        headers = ["Rank", "Content (Preview)", "Aggregated Score"]
        return tabulate(table_data, headers=headers, tablefmt="grid")

    def format_results(self, re_ranked_docs):
        """
        Format the re-ranked documents for better readability.

        :param re_ranked_docs: List of re-ranked documents with scores.
        :return: A formatted string representation of the results.
        """
        #if not re_ranked_docs:
        #    return "No documents re-ranked."

        table_data = [
            [i + 1, doc.page_content[:100] + "...", round(doc.metadata["score"], 4)]
            for i, doc in enumerate(re_ranked_docs)
        ]

        headers = ["Rank", "Content (Preview)", "Score"]
        return tabulate(table_data, headers=headers, tablefmt="grid")


def test_normal():
    # Initialize the Retriever and ReRanker
    retriever = Retriever()
    reranker = CrossEncoderReRanker()

    # Define the test query
    query_text = "What is an example of document retrieval?"

    # Retrieve documents using the retriever
    print("\n--- Retrieving Documents ---")
    retrieved_docs = retriever.retrieve(query_text)
    if not retrieved_docs:
        print("No documents retrieved. Cannot proceed with re-ranking.")
        return

    # Display the retrieved documents
    print(f"\nRetrieved {len(retrieved_docs)} documents:")
    print(retriever.format_results(retrieved_docs))

    # Re-rank the retrieved documents
    print("\n--- Re-ranking Documents ---")
    re_ranked_docs = reranker.re_rank_documents(query_text, retrieved_docs, top_k=5)

    if not re_ranked_docs:
        print("No documents re-ranked. Check for issues in re-ranking.")
        return

    # Display the re-ranked results
    print("\nRe-ranked Documents:")
    print(reranker.format_results(re_ranked_docs))

def test_script_with_aggregated_reranking():
    # Initialize the Retriever and ReRanker
    retriever = Retriever()
    reranker = CrossEncoderReRanker()

    # Define the test query
    query_text = "Age: 78, Gender: female, Medications: Ciprofloxacin (5mg diphenoxylate & 0.05mg atropine QDS), Tolterodine IR (2mg BD), Brinzolamide (1 drop TDS), Conditions: Severe diarrhoea, dementia, overactive bladder syndrome, Chronic glaucoma"

    # Retrieve documents and generated queries using the retriever
    print("\n--- Retrieving Documents ---")
    retrieved_docs, generated_queries = retriever.retrieve_multi_query(query_text)
    if not retrieved_docs:
        print("No documents retrieved. Cannot proceed with re-ranking.")
        return

    # Display the retrieved documents
    print(f"\nRetrieved {len(retrieved_docs)} documents:")
    print(retriever.format_results(retrieved_docs))

    # Display the generated queries
    print("\nGenerated Queries:")
    for query in generated_queries:
        print(query)

    # Re-rank the retrieved documents across all queries
    print("\n--- Re-ranking Documents Across Queries ---")
    re_ranked_docs = reranker.re_rank_documents_across_queries(generated_queries, retrieved_docs)

    # Display the re-ranked results
    print("\nRe-ranked Documents Across Queries:")
    print(reranker.format_results_multi_query(re_ranked_docs))


if __name__ == "__main__":
    try:
        test_script_with_aggregated_reranking()

    except Exception as e:
        print(f"\nAn error occurred during testing: {e}")

    finally:
        print("\nTesting complete.")
