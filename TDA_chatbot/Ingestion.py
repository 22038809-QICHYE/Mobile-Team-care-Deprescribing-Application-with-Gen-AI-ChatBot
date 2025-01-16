from langchain_text_splitters import RecursiveCharacterTextSplitter
import PyPDF2
import csv
import math
from Chroma import ChromaManager

class Ingestion_file:
    def __init__(self):
        """Initializes the Ingestion class"""
        pass

    def extract_text_from_pdf(self, pdf_path):
        """
        Extract text from a PDF file.
        :param pdf_path: Path to the PDF file.
        :return: Extracted text as a single string.
        """
        text = ""
        try:
            with open(pdf_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Error reading PDF file: {e}")
        return text

    def chunk_pdf_text(self, pdf_path, chunk_size=250, chunk_overlap=50, debug=False):
        """
        Chunk text from a PDF file into manageable pieces and add to ChromaDB.
        :param pdf_path: Path to the PDF file.
        :param chunk_size: Size of each chunk.
        :param chunk_overlap: Overlap size between chunks.
        :param debug: Whether to display debugging information.
        :return: List of text chunks added to ChromaDB.
        """
        pdf_text = self.extract_text_from_pdf(pdf_path)

        if not pdf_text.strip():
            print("No text found in PDF.")
            return []

        try:
            chunking = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
            )
            chunks = chunking.split_text(pdf_text)
        except Exception as e:
            print(f"Error during PDF text splitting: {e}")
            return []

        if debug:
            for i, chunk in enumerate(chunks):
                print(f"Chunk #{i + 1}:\n{chunk}\nSize: {len(chunk)}\n{'-'*20}")

        documents = [
            {"id": f"pdf_{i + 1}", "text": chunk, "metadata": {"source": pdf_path, "chunk_index": i + 1}}
            for i, chunk in enumerate(chunks)
        ]

        return documents

    def chunk_csv_text(self, csv_path, chunk_size=1, debug=False):
        """
        Chunk rows from a CSV file into manageable pieces and add to ChromaDB.
        :param csv_path: Path to the CSV file.
        :param chunk_size: Number of rows per chunk.
        :param debug: Whether to display debugging information.
        :return: List of text chunks added to ChromaDB.
        """
        rows = []
        try:
            with open(csv_path, mode='r', newline='', encoding='latin1') as file:
                reader = csv.DictReader(file)

                # Ensure CSV has valid headers
                if not reader.fieldnames:
                    print("No headers found in the CSV file.")
                    return []

                # Parse rows
                for row in reader:
                    if isinstance(row, dict):
                        # Convert dictionary row to string
                        row_str = " ".join([f"{key}: {value}" for key, value in row.items()])
                        rows.append(row_str)
                    else:
                        print(f"Skipping unexpected row format: {row}")
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            return []

        # Check if rows exist before chunking
        if not rows:
            print("No valid rows found in the CSV.")
            return []

        try:
            total_rows = len(rows)
            num_chunks = math.ceil(total_rows / chunk_size)
            chunks = [
                " ".join(rows[i * chunk_size:(i + 1) * chunk_size])
                for i in range(num_chunks)
            ]
        except Exception as e:
            print(f"Error during CSV chunking: {e}")
            return []

        if debug:
            for i, chunk in enumerate(chunks):
                print(f"Chunk #{i + 1}:\n{chunk}\n{'-'*20}")

        documents = [
            {"id": f"csv_{i + 1}", "text": chunk, "metadata": {"source": csv_path, "chunk_index": i + 1}}
            for i, chunk in enumerate(chunks)
        ]
        return documents


def test_chunking_functions():
    """
    Test the PDF and CSV chunking functions with sample inputs and add them to ChromaDB.
    """
    # Assuming ChromaManager instance is initialized correctly
    chroma_manager = ChromaManager()

    ingesting = Ingestion_file()

    # Test PDF Chunking and adding to ChromaDB
    pdf_path = r"C:\VS_CODES\RAG\data source\BEERS J American Geriatrics Society - 2023 -  - American Geriatrics Society 2023 updated AGS Beers Criteria  for potentially.pdf"  # Replace with your PDF path
    print("\n=== Testing PDF Chunking ===")
    try:
        pdf_chunks = ingesting.chunk_pdf_text(pdf_path, chunk_size=250, chunk_overlap=50, debug=True)
        if pdf_chunks:
            print(f"PDF chunking successful. Total chunks created: {len(pdf_chunks)}")
            chroma_manager.add_documents(pdf_chunks)
        else:
            print("No chunks were created for the PDF.")
    except Exception as e:
        print(f"PDF chunking failed: {e}")

    # Test CSV Chunking and adding to ChromaDB
    csv_path = r"C:\VS_CODES\RAG\data source\csv\Table 2.csv"  # Replace with your CSV path
    print("\n=== Testing CSV Chunking ===")
    try:
        csv_chunks = ingesting.chunk_csv_text(csv_path, chunk_size=1, debug=True)
        if csv_chunks:
            chroma_manager.add_documents(csv_chunks)
            print(f"CSV chunking successful. Total chunks created: {len(csv_chunks)}")
        else:
            print("No chunks were created for the CSV.")
    except Exception as e:
        print(f"CSV chunking failed: {e}")


if __name__ == "__main__":
    try:
        test_chunking_functions()
    except Exception as e:
        print(f"An error occurred during the test: {e}")
    finally:
        print("\nTest script execution completed.")
