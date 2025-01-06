# Mobile-Team-care-Deprescribing-Application-with-Gen-AI-ChatBot
For Integration and Deployment
> You can understand this project better on [YouTube]([https://youtu.be/dXxQ0LR-3Hg](https://www.youtube.com/watch?v=T-D1OfcDW1M&list=PLEJnINKHyZIBZZxkSNafHQMDdg5Lf3O3W&pp=gAQB)).

# Introduction
------------
The TDA Chat App is a Python application that allows you to chat with multiple PDF documents. You can ask questions about the PDFs using natural language, and the application will provide relevant responses based on the content of the documents. This app utilizes a language model to generate accurate answers to your queries. Please note that the app will only respond to questions related to the loaded PDFs.

# How It Works
------------

![System Architecture Diagram](./Sys_Arc/Sys_Arc.jpg)

The application follows these steps to respond to your questions:

1. PDF/CSV Loading: The app reads multiple PDF or CSV documents and extracts their text content.

2. Text Chunking: The extracted text is divided into smaller chunks that can be processed effectively.

3. Vector Database: The chunks will be embedded via an embedding model and stored in the chromaDB.

5. Language Model: The application utilizes a language model to generate vector representations (embeddings) of the text chunks.

6. Similarity Matching: When you ask a question, the app compares it with the text chunks and identifies the most semantically similar ones.

7. Response Generation: The selected chunks are passed to the language model, which generates a response based on the relevant content of the PDFs.

# Dependencies and Installation
----------------------------
To install the MultiPDF Chat App, please follow these steps:

1. Clone the repository to your local machine.

2. Install the required dependencies by running the following command:
   ```
   pip install -r Requirements.txt
   ```

3. Obtain an API key from OpenAI and add it to the `.env` file in the project directory.
   ```
   CHROMA_PATH = "C:\VS_CODES\RAG\Collections"
   COLLECTION_NAME="Unstructured_data"
   REDIS_URL="redis://default:ytXIaoFI74f4TT8LfSBlfBuYCNFRjv3B@redis-12846.c252.ap-southeast-1-1.ec2.redns.redis-cloud.com:12846"
   ```

# Usage
-----
To use the MultiPDF Chat App, follow these steps:

1. Ensure that you have installed the required dependencies and added the OpenAI API key to the `.env` file.

2. Run the `main.py` file using the Streamlit CLI. Execute the following command:
   ```
   streamlit run app.py
   ```

3. The application will launch in your default web browser, displaying the user interface.

4. Load multiple PDF documents into the app by following the provided instructions.

5. Ask questions in natural language about the loaded PDFs using the chat interface.

