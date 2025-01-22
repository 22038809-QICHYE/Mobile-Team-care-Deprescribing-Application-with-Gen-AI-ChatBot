from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_community.cache import InMemoryCache
from langchain_core.globals import set_llm_cache
from RAG_V3_2 import RAGSystem #QC

#=== QC ===
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
    Your tone should always be kind, empathetic, and supportive, ensuring the user feels heard and cared for.
    Start responses with warm acknowledgments like "Thank you for sharing," or "I understand this can be a complex decision."
    If no relevant information is found in the documentation, provide an accurate response based on general knowledge and kindly clarify this, using phrases such as:
    "Based on general best practices..."
    or "Here is what I can suggest from widely accepted guidance..."
    Follow best practices in medication management and always prioritize patient safety. 
    If the decision to deprescribe involves significant risks or requires specialized input, gently recommend involving a healthcare professional. Use reassuring language, such as:
    "It is always a good idea to consult with your healthcare provider to ensure the best outcome for your health."
    or "Together with your healthcare professional, you can explore the safest and most effective options."
    If deprescribing is recommended, provide alternative strategies to manage their condition and express encouragement, e.g.,
    "There are several options we can explore together to support your health."
    or "Here are a few strategies that may help you feel better while reducing or stopping this medication."
    Please be kind and friendly when responding to users.

    If there are topics that are not relevant to medication management, kindly reject their request and kindly clarify that you can only answer questions related to medication management.
    Chat History: {chat_history}

    User: {input}
""")

validation_prompt = PromptTemplate.from_template("""
    System: You are a decision-support AI tasked with safely deprescribing medications for patients. 
    Your tone should always be kind, empathetic, and supportive, ensuring the user feels heard and cared for.
    Start responses with warm acknowledgments like "Thank you for sharing," or "I understand this can be a complex decision."
    Check that patient information consists of the following fields:
    Age, Gender, Medications, Medical Conditons.
    At least one medication and one medical condition.
    If any of these required fields are not stated, ask the patient again for the required fields.
    

    Chat History: {chat_history}

    Patient Information: {input}
""")
def extract_required_fields(input_text):
    """
    Extract Age, Gender, Medications, and Conditions from the user input.
    """
    # Placeholder for actual extraction logic (use regex or NLP for real-world scenarios)
    extracted_fields = {
        "Age": None,
        "Gender": None,
        "Medications": None,
        "Conditions": None
    }
    # Parsing
    for line in input_text.split("\n"):
        if "age" in line.lower():
            extracted_fields["Age"] = line.split(":")[1].strip()
        elif "gender" in line.lower():
            extracted_fields["Gender"] = line.split(":")[1].strip()
        elif "medications" in line.lower():
            extracted_fields["Medications"] = line.split(":")[1].strip()
        elif "conditions" in line.lower():
            extracted_fields["Conditions"] = line.split(":")[1].strip()

    return extracted_fields

def generate(query, model, chat_history):
    # Join chat history into a single string
    chat_string = "|".join(msg["content"] for msg in chat_history)

    # Step 1: Validate the input data
    validation_prompt_text = validation_prompt.format(
        input=query,
        chat_history=chat_string
    )
    validation_response = model.invoke(validation_prompt_text)

    if validation_response.content.lower().strip() != "true":
        # Validation failed, return the validation error message
        return validation_response.content
    
    # Step 45: Extract required fields
    extracted_fields = extract_required_fields(query)

    # Format extracted fields for retrieval
    formatted_query = f"(Age: {extracted_fields['Age']}, Gender: {extracted_fields['Gender']}, Medications: {extracted_fields['Medications']}, Conditions: {extracted_fields['Conditions']})"

    # Step 3: Perform retrieval using formatted query
    retrieved_context = rag.process_query(formatted_query, "gpt-4")
    print(retrieved_context)

    # Step 3: Generate a response using retrieved context
    response_prompt_text = prompt.format(
        input=query,
        chat_history=chat_string,
        retrieved_context=retrieved_context
    )
    response = model.invoke(response_prompt_text)

    # Append the generated response to chat history
    chat_history.append({
        "role": "assistant",
        "content": response.content
    })

    return response.content
