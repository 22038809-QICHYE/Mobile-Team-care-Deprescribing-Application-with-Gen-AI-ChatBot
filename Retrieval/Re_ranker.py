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

    def re_rank_documents(self, query_text, retrieved_docs, top_k=5):
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

    def format_results(self, re_ranked_docs):
        """
        Format the re-ranked documents for better readability.

        :param re_ranked_docs: List of re-ranked documents with scores.
        :return: A formatted string representation of the results.
        """
        if not re_ranked_docs:
            return "No documents re-ranked."

        table_data = [
            [i + 1, doc.page_content[:100] + "...", round(doc.metadata["score"], 4)]
            for i, doc in enumerate(re_ranked_docs)
        ]

        headers = ["Rank", "Content (Preview)", "Score"]
        return tabulate(table_data, headers=headers, tablefmt="grid")

def test_script1():
    # Initialize the Retriever and ReRanker
    retriever = Retriever()  # Ensure verbose is True for debugging
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


if __name__ == "__main__":
    try:
        test_script1()

    except Exception as e:
        print(f"\nAn error occurred during testing: {e}")

    finally:
        print("\nTesting complete.")