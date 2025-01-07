# Mobile-Team-care-Deprescribing-Application-with-Gen-AI-ChatBot
For Integration and Deployment

> You can understand the components of this project better at [YouTube playlist](https://www.youtube.com/watch?v=T-D1OfcDW1M&list=PLEJnINKHyZIBZZxkSNafHQMDdg5Lf3O3W&pp=gAQB).

# Introduction
------------
The TDA chatbot is a robust AI-powered information retrieval and conversational platform designed to enable users to access relevant documents and receive intelligent responses efficiently. By combining Natural Language Understanding (NLU), advanced embedding models, and retrieval-augmented generation (RAG), the system streamlines document ingestion, retrieval, and conversational response generation. With its modular architecture, the platform supports document management via an Admin UI, high-accuracy retrieval through ChromaDB, and dynamic response generation using large language models like OpenAI and Gemini.

# How It Works
------------

![System Architecture Diagram](./Sys_Arc/Sys_Arc.jpg)

The application follows these steps to respond to your questions:

1. Admin and Document Management: Administrators manage the system through an Admin UI, where documents are uploaded and organized into collections. The Admin UI facilitates chunking and embedding documents using a embedding model.
The embedded documents are indexed and stored in ChromaDB, a vector database optimized for high-speed and scalable retrieval.

2. Document Ingestion: The ingestion pipeline preprocesses the uploaded documents by chunking them into smaller parts, embedding the content, and indexing the resulting embeddings in ChromaDB.
This process ensures the database is ready for efficient similarity-based searches and retrieval.

3. User Query and Interaction: Users interact with the system through a web-based chatbot built on Streamlit. The chatbot processes user queries along with the conversation's chat history to maintain context.
The chatbot uses an NLU engine (Dialogflow) to interpret the query and generate a structured prompt for further processing.

4. Retriever Module: The query is embedded using the same BioBERT model to ensure embedding compatibility with ChromaDB.
The embedded query is used to retrieve relevant documents from ChromaDB based on vector similarity.
Retrieved documents are reranked to identify the most relevant ones, leveraging a re-ranking model for higher precision.

5. Augmentation and Response Generation: The top-ranked document is selected and combined with the user query and chat history to form an augmented prompt.
This augmented prompt is processed by a generation module powered by OpenAI and Gemini, which generates contextually rich and accurate responses.

6. Database Integration: An RDBMS database maintains user information, chat history, and system status, ensuring a seamless user experience and robust data management.

7. Response Delivery: The generated response is sent back to the user through the chatbot interface, completing the conversational loop.

# Dependencies and Installation
----------------------------
To install the TDA Chatbot, please follow these steps:

1. Clone the repository to your local machine.

2. Install the required dependencies by running the following command:
   ```
   pip install -r Required.txt
   ```

3. Obtain an API key from OpenAI and Gimini and add it to the `.env` file in the project directory.
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

