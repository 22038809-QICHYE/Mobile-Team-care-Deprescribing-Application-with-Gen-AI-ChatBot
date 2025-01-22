from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_community.cache import InMemoryCache
from langchain_core.globals import set_llm_cache
from RAG_V3_2 import RAGSystem  # QC
import json

# === QC ===
rag = RAGSystem()

current_info = ""
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

chosen_model = setupModel("gpt")

json_model = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key=GPT4.api_key)

decision_model = json_model.bind(response_format={"type": "json_object"})

def get_info(current_info, model):
    prompt = PromptTemplate.from_template("""
    System: You are a patient information validator.
    Check that patient information consists of the following fields:
    Age, Gender, Medications, Medical Conditions. 
    At least one medication and one medical condition.
    If any of these required fields are not stated, ask the patient for the required fields.
    Always maintain a kind and friendly tone when interacting with users.

    Patient Information: {current_info}
    """)

    get_info_prompt_text = prompt.format(
        current_info=current_info
        )

    response = model.invoke(get_info_prompt_text)

    return response.content

def generate(current_info, model):
    prompt = PromptTemplate.from_template("""
    System: You are a decision-support AI specializing in safely deprescribing medications for patients.
    If the documentation lacks relevant information, respond accurately based on general knowledge, clearly indicating so.
    Adhere to best practices in medication management, prioritizing patient safety.
    When deprescribing poses significant risks or needs specialized input, advise involving a healthcare professional and outline key discussion points.
    If deprescribing is advisable, suggest alternative strategies to manage the condition.
    Always maintain a kind and friendly tone when interacting with users.

    Patient Information: {current_info}
    Documentations: {retrieved_context}
    """)
    retrieved_context = rag.process_query(current_info, "gpt-4")
    print("Retrieved Context:\n", retrieved_context)
    prompt_text = prompt.format(
        current_info=current_info, 
        retrieved_context=retrieved_context
        )

    response = model.invoke(prompt_text)

    return response.content

def check_score(data):
    data_dict = json.loads(data.strip())  # Ensure JSON is parsed correctly
    if type(data_dict.get('score')) is not bool:
        return data_dict.get('score') == "true"
    else:
        return data_dict.get('score') is True

def validate(model, current_info):

    validation_prompt = PromptTemplate.from_template("""
    System: You are a patient information validator.
    Check that patient information consists of the following fields:
    Age, Gender, Medications and Medical Conditions.
    There should be at least one medication and one medical condition.
    Give a binary score 'true' or 'false' score to indicate whether all the patient information is availablen. \n
    Provide the binary score as a JSON with a single key 'score' and no preamble or explanation.

    Current Patient Information: {current_info}

    """)

    # Step 1: Validate the input data
    validation_prompt_text = validation_prompt.format(
        current_info=current_info
    )
    validation_response = model.invoke(validation_prompt_text)
    return validation_response.content

def retieve_patient_info(query, model, current_info):

    retrieve_info_prompt = PromptTemplate.from_template("""
    System: You are a patient information retriever.
    Extract only patient information from the query for retrieval.  
    Check the current patient information provided and add any missing information from the query.
    Take note that the number provided is the age of the patient.
    M means male, F means female, write the full form in the response.
    If the field is not provided, leave it empty.
    Current Patient Information: {current_info}
    Query: {input}
    Send back the patient information in the following format:
    Age: 
    Gender:
    Medications:
    Medical Conditions:
    """)

    retrieve_info_prompt_text = retrieve_info_prompt.format(
        input=query,
        current_info=current_info
    )
    info = model.invoke(retrieve_info_prompt_text)
    return info.content


