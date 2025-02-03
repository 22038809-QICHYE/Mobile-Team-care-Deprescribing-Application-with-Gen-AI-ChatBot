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

4. Retriever Module: The query is embedded using the same embedding model to ensure embedding compatibility with ChromaDB.
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
   python -m pip install -r requirements.txt

   ```

3. Obtain an API key from OpenAI and Gimini and add it to the `.env` file in the project directory.
   ```
   CHROMA_PATH = "C:\VS_CODES\RAG\Collections"
   COLLECTION_NAME="Unstructured_data"
   REDIS_URL="redis://default:ytXIaoFI74f4TT8LfSBlfBuYCNFRjv3B@redis-12846.c252.ap-southeast-1-1.ec2.redns.redis-cloud.com:12846"
   OPENAI_API_KEY="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"
   ```

# Usage
-----
To use the MultiPDF Chat App, follow these steps:

1. Ensure that you have installed the required dependencies and added the OpenAI API key to the `.env` file.

2. Run the `chatbotapp.py` file using the Streamlit CLI. Execute the following command:
   ```
   python chatbotapp.py
   ```

3. The application will launch in your default web browser, displaying the user interface.

4. Load multiple PDF documents into the app by following the provided instructions.

5. Ask questions in natural language about the loaded PDFs using the chat interface.


To use the Admin Web Page, follow these steps:

1. Ensure that you have installed the required dependencies

2. Before running `app.py`, open the `app.py` code with Visual Studio Code at line 16, ensure that `app.config['UPLOAD_FOLDER'] = 'C:/your/path'` is set to where your upload folder is.

3. When running `app.py` a link will appear in your terminal, copy paste the link into your desired browser or `ctrl + left click` the link which will send you to the link via your default web browser.

4. The application will launch in your default web browser, displaying a welcome interface.

5. Click login on the top left of the screen or click any of the buttons to enter the login screen. Username: admin, Password: admin

6. Login with the username and password.

7. When logged in you are able to view, add , edit, delete resources and users.

8. When adding user, simply fill in the required blanks. For the `Make this user an admin` checkbox, by ticking it you 
   will be adding an admin who is able to login on the ChatBot web page and the Admin web page. If it is not ticked, 
   the user will not be allowed to access the Admin page even with the correct username and password.

9. When adding resource, ensure that file is in PDF or CSV format then proceed to fill in the blanks.

10. When editing simply change the values and click the edit button.

11. When deleting resource, a confirmation button will appear on your screen when clicking delete, simply press `OK` to carry on.

