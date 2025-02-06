# Neural Rerankers
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from Retrieval import Retriever
from tabulate import tabulate
# Traditional Scoring Techniques
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from rank_bm25 import BM25Okapi


# Neural Rerankers
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
            score_map = {doc.id: 0 for doc in retrieved_docs}

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

#=== Testing ===
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

def test_with_aggregated_reranking():
    # Initialize the Retriever and ReRanker
    retriever = Retriever()
    reranker = CrossEncoderReRanker()

    # Define the test query
    #query_text = "Age: 78, Gender: male, Medications: Digoxin (OD 0.125mg), Fluticasone (BID 2 puff), Warfarin (OD 5), Conditions: Essential hypertension (BA00), Iron deficiency anaemia (3A00), Mixed hyperlipidaemia (5C80.2)"

    query_text = "Age: 92, Gender: male, Medication: Metoprolol (OD 100mg), Warfarin (OD 5mg), Amiodarone (OD 800mg), Simvastatin (OD 10mg), Condition: Obesity in adults, Iron deficiency anaemia, Mixed hyperlipidaemia, Osteoporosis, Congestive heart failure, Acute myocardial infarction, Intermediate hyperglycaemia"

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

def test_rephrase_query():
    # Initialize the Retriever and ReRanker
    retriever = Retriever()
    reranker = CrossEncoderReRanker()

    # Define the test query
    query_text = "Age: 78, Gender: male, Medications: Digoxin (OD 0.125mg), Fluticasone (BID 2 puff), Warfarin (OD 5), Conditions: Essential hypertension (BA00), Iron deficiency anaemia (3A00), Mixed hyperlipidaemia (5C80.2)"

    # Retrieve documents using the retriever
    print("\n--- Retrieving Documents ---")
    retrieved_docs = retriever.retrieve_rephrase_query(query_text)
    if not retrieved_docs:
        print("No documents retrieved. Cannot proceed with re-ranking.")
        return

    # Display the retrieved documents
    print(f"\nRetrieved {len(retrieved_docs)} documents:")
    print(retriever.format_results(retrieved_docs))

    # Re-rank the retrieved documents
    print("\n--- Re-ranking Documents ---")
    re_ranked_docs = reranker.re_rank_documents(query_text, retrieved_docs)

    if not re_ranked_docs:
        print("No documents re-ranked. Check for issues in re-ranking.")
        return

    # Display the re-ranked results
    print("\nRe-ranked Documents:")
    print(reranker.format_results(re_ranked_docs))

def test_ensemble_retriever():
    # Initialize the Retriever and ReRanker
    retriever = Retriever()
    reranker = CrossEncoderReRanker()

    # Define the test query
    query_text = "Age: 78, Gender: female, Medications: Ciprofloxacin (5mg diphenoxylate & 0.05mg atropine QDS), Tolterodine IR (2mg BD), Brinzolamide (1 drop TDS), Conditions: Severe diarrhoea, dementia, overactive bladder syndrome, Chronic glaucoma"

    # Retrieve documents using the retriever
    print("\n--- Retrieving Documents ---")
    retrieved_docs = retriever.retrieve_ensemble(query_text)
    if not retrieved_docs:
        print("No documents retrieved. Cannot proceed with re-ranking.")
        return

    # Display the retrieved documents
    print(f"\nRetrieved {len(retrieved_docs)} documents:")
    print(retriever.format_results(retrieved_docs))

    # Re-rank the retrieved documents
    print("\n--- Re-ranking Documents ---")
    re_ranked_docs = reranker.re_rank_documents(query_text, retrieved_docs)

    if not re_ranked_docs:
        print("No documents re-ranked. Check for issues in re-ranking.")
        return

    # Display the re-ranked results
    print("\nRe-ranked Documents:")
    print(reranker.format_results(re_ranked_docs))
#===============



# Traditional Scoring Techniques
class BM25ReRanker:
    def __init__(self):
        """
        Initialize the BM25 re-ranker.
        """
        nltk.download('punkt') #only need to download once
        nltk.download('stopwords') #only need to download once
        self.bm25 = None  # Will be initialized dynamically

    def tokenize_text(self, text):
        """
        Tokenize text by:
        - Lowercasing
        - Removing stopwords
        - Keeping only alphanumeric words

        :param text: The document or query text.
        :return: Tokenized word list.
        """
        stop_words = set(stopwords.words("english"))
        return [
            word.lower() for word in word_tokenize(text)
            if word.isalnum() and word.lower() not in stop_words
        ]

    def rerank_documents(self, query, retrieved_docs, top_n=10):
        """
        Rerank retrieved documents based on BM25 scores for a given query.

        :param query: The query to search for in the documents.
        :param retrieved_docs: List of retrieved document objects with 'page_content' and 'metadata'.
        :param top_n: Number of top-ranked documents to return (default: 10).
        :return: List of dictionaries with document id, BM25 score, and text.
        """
        if not retrieved_docs:
            print("No retrieved documents provided for re-ranking.")
            return []

        # Debugging - Print retrieved document format
        # print(f"DEBUG: Retrieved Documents Type: {type(retrieved_docs)}")
        # print(f"DEBUG: Sample Document: {retrieved_docs[0] if retrieved_docs else 'No Documents'}")

        # Extract text and IDs correctly
        try:
            get_text = lambda doc: doc.page_content  # Text content
            get_id = lambda doc: doc.metadata.get("id", "unknown")  # Document ID from metadata
        except AttributeError:
            print("Error: Retrieved documents are not in the expected format.")
            return []

        # Extract and tokenize document texts
        document_texts = [get_text(doc) for doc in retrieved_docs]
        tokenized_docs = [self.tokenize_text(text) for text in document_texts]

        # Initialize BM25 model with optimized parameters
        self.bm25 = BM25Okapi(tokenized_docs, k1=1.5, b=0.75)

        # Tokenize the query
        tokenized_query = self.tokenize_text(query)

        # Compute BM25 scores for the query
        scores = self.bm25.get_scores(tokenized_query)

        # Build ranked document list
        ranked_documents = [
            {
                "id": get_id(doc),
                "score": score,
                "text": get_text(doc),
            }
            for doc, score in zip(retrieved_docs, scores)
        ]

        # Sort documents by BM25 score in descending order and return top_n
        ranked_documents = sorted(ranked_documents, key=lambda x: x["score"], reverse=True)

        return ranked_documents[:top_n]

#=== Testing ===
def test_BM25_ReRanker():
    from Retrieval import Retriever

    # Initialize the Retriever and BM25 ReRanker
    retriever = Retriever()
    bm25_reranker = BM25ReRanker()

    # Example query
    #query = "Age: 78, Gender: male, Medications: Digoxin (OD 0.125mg), Fluticasone (BID 2 puff), Warfarin (OD 5), Conditions: Essential hypertension (BA00), Iron deficiency anaemia (3A00), Mixed hyperlipidaemia (5C80.2)"

    query = "Age: 92, Gender: male, Medication: Metoprolol (OD 100mg), Warfarin (OD 5mg), Amiodarone (OD 800mg), Simvastatin (OD 10mg), Condition: Obesity in adults, Iron deficiency anaemia, Mixed hyperlipidaemia, Osteoporosis, Congestive heart failure, Acute myocardial infarction, Intermediate hyperglycaemia"

    # Retrieve documents and generated queries using the retriever
    print("\n--- Retrieving Documents ---")
    retrieved_docs, generated_queries = retriever.retrieve_multi_query(query)
    # Display the generated queries
    print("\nGenerated Queries:")
    for GEN_query in generated_queries:
        print(GEN_query)

    if not retrieved_docs:
        print("No documents retrieved. Cannot proceed with re-ranking.")
        return "No documents retrieved."

    # Display the retrieved documents
    print(f"\nRetrieved {len(retrieved_docs)} documents:")
    print(retriever.format_results(retrieved_docs))

    # Re-rank the retrieved documents across all queries
    print("\n--- Re-ranking Documents ---")

    # Get top 10 ranked documents
    top_ranked_docs = bm25_reranker.rerank_documents(query, retrieved_docs, top_n=10)

    # Display top ranked documents
    print("\nTop 10 Ranked Documents:")
    for doc in top_ranked_docs:
        print(f"Document ID: {doc['id']} | Score: {doc['score']} | Text: {doc['text'][:100]}...")
#===============

if __name__ == "__main__":
    try:
        test_with_aggregated_reranking()
    except Exception as e:
        print(f"\nAn error occurred during testing: {e}")
    finally:
        print("\nTesting complete.")

