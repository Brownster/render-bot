#!pip install openai -q
#!pip install langchain -q
#!pip install chromadb -q
#!pip install tiktoken -q
#!pip install pypdf -q
#!pip install unstructured[local-inference] -q
#!pip install gradio -q

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores.chroma import Chroma
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.document_loaders import DirectoryLoader
from langchain.chains.question_answering import load_qa_chain
from langchain.chains import RetrievalQA
import os
os.environ["OPENAI_API_KEY"] = "aaaa"
from langchain.chat_models import ChatOpenAI
llm = ChatOpenAI(temperature=0,model_name="gpt-4")

# Check if any document loaders are specified
loaders = []
if os.path.exists('./docs/'):
    pdf_loader = DirectoryLoader('./docs/', glob="**/*.pdf")
    excel_loader = DirectoryLoader('./docs/', glob="**/*.txt")
    word_loader = DirectoryLoader('./docs/', glob="**/*.docx")
    loaders = [pdf_loader, excel_loader, word_loader]

# Load documents and embed them if loaders are specified
documents = []
if loaders:
    # Load documents from loaders
    for loader in loaders:
        documents.extend(loader.load())
    # Split documents into chunks and embed them
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    documents = text_splitter.split_documents(documents)
    persist_directory = './mykb_db'
    embeddings = OpenAIEmbeddings()
    collection_name = "mykb_db"
    if documents:
        vectorstore = Chroma.from_documents(documents, embeddings, collection_name=collection_name, persist_directory=persist_directory)
        vectorstore.add_documents(documents)
        vectorstore.persist()
# Initialise Langchain - Conversation Retrieval Chain
if loaders:
    # Use the document-based vectorstore if documents were loaded
    vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    qa = ConversationalRetrievalChain.from_llm(ChatOpenAI(temperature=0), vectorstore.as_retriever())
else:
    # Use an empty vectorstore if no documents were loaded
    persist_directory = './mykb_db'
    collection_name = "mykb_db"
    vectorstore = Chroma(persist_directory=persist_directory, collection_name=collection_name, embedding_function=OpenAIEmbeddings())
    qa = ConversationalRetrievalChain.from_llm(ChatOpenAI(temperature=0), vectorstore.as_retriever())

# Front end web app
import gradio as gr

def set_api_key(api_key):
    os.environ['OPENAI_API_KEY'] = api_key
    global llm
    llm = ChatOpenAI(temperature=0, model_name="gpt-4", openai_api_key=api_key)

with gr.Blocks() as demo:
    chatbot = gr.Chatbot()
    msg = gr.Textbox()
    clear = gr.Button("Clear")
    set_api_key_button = gr.Button("Set API Key")
    api_key_input = gr.Textbox(placeholder="Enter OpenAI API Key", type="password")
    
    chat_history = []
    
    def user(user_message, history):
        # Get response from QA chain
        response = qa({"question": user_message, "chat_history": history})
        # Append user message and response to chat history
        history.append((user_message, response["answer"]))
        return gr.update(value=""), history
    msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False)
    clear.click(lambda: None, None, chatbot, queue=False)
    set_api_key_button.click(set_api_key, [api_key_input], None, queue=False)

if __name__ == "__main__":
    demo.launch(debug=True)
