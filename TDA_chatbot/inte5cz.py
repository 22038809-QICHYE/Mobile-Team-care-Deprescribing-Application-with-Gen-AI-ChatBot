from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_community.cache import InMemoryCache
from langchain_core.globals import set_llm_cache
from RAG_V3_2 import RAGSystem  # QC

# === QC ===
rag = RAGSystem()

# Add cache to langchain
set_llm_cache(InMemoryCache())

# Classifying models
class LLMmodel:
    def __init__(self, model, api_key):
        self.api_key = api_key
        self.model = model

# Setting up different models and API keys
GPT4 = LLMmodel("gpt-4", "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")
GEMINI = LLMmodel("gemini-1.5-flash", "AIzaSyBKseORSyKLbbmc9hoX-4N0LUr4ApWWgOA")

def setupModel(modelname):
    if modelname == "gpt":
        model = ChatOpenAI(model="gpt-4", openai_api_key=GPT4.api_key)
    elif modelname == "gemini":
        model = ChatGoogleGenerativeAI(model=GEMINI.model, google_api_key=GEMINI.api_key)
    return model

# Prompt Engineering
prompt = PromptTemplate.from_template("""
    System: You are a decision-support AI tasked with safely deprescribing medications for patients.
    If no relevant information is found in the documentation, provide an accurate response based on general knowledge and clarify that it is based on general knowledge.
    Follow best practices in medication management and always prioritize patient safety.
    If the decision to deprescribe involves significant risks or requires specialized input,
    recommend involving a healthcare professional and highlight key discussion points.
    If deprescribing is recommended, provide alternative strategies to manage their condition.
    Please be kind and friendly when responding to users.

    Chat History: {chat_history}

    User: {input}

    Retrieved Context: {retrieved_context}
""")

validation_prompt = PromptTemplate.from_template("""
    System: You are a patient information validator.
    Check that patient information consists of the following fields:
    Age, Gender, Medications, Medical Conditions.
    At least one medication and one medical condition.
    If any of these required fields are not stated, ask the patient again for the required fields.
    If all patient information is available, reply true with no explanation.
    No need to ask for other questions, just take in the four required fields.

    Chat History: {chat_history}

    Patient Information: {input}
""")

def generate(query, model, chat_history):
    # Join chat history into a single string
    chat_string = "|".join(msg["content"] for msg in chat_history)

    # Step 1: Validate the input data
    validation_prompt_text = validation_prompt.format(
        input=query,
        chat_history=chat_string
    )
    print("Validation Prompt Sent to Model:\n", validation_prompt_text)
    validation_response = model.invoke(validation_prompt_text)
    print("Validation Response:\n", validation_response.content)

    if validation_response.content.lower().strip() != "true":
        # Validation failed, return the validation error message
        return validation_response.content

    # Extract only patient information from the query for retrieval
    patient_info = query  # This assumes `query` contains the patient data.

    # Step 2: Perform retrieval with patient information
    retrieved_context = rag.process_query(patient_info, "gpt-4")
    print("Retrieved Context:\n", retrieved_context)

    # Step 3: Generate a response using retrieved context
    response_prompt_text = prompt.format(
        input=query,
        chat_history=chat_string,
        retrieved_context=retrieved_context
    )
    print("Response Prompt Sent to Model:\n", response_prompt_text)
    response = model.invoke(response_prompt_text)
    print("Response from Model:\n", response.content)

    # Append the generated response to chat history
    chat_history.append({
        "role": "assistant",
        "content": response.content
    })

    return response.content
