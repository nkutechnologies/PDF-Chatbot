import streamlit as st
from streamlit_option_menu import option_menu
import os
from dotenv import load_dotenv
import fitz
import pinecone
from langchain.embeddings.openai import OpenAIEmbeddings
from flask import Flask, render_template, request, jsonify
from langchain.chains.question_answering import load_qa_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Pinecone
from langchain.llms import OpenAI

qa_memory = []
label_visibility='collapse'
load_dotenv()
# Access the environment variables
openai_api_key =os.getenv("OPEN_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = "gcp-starter"

# Initialize Streamlit
st.set_page_config(
    page_title="PDF Bot",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Initialize Pinecone


# Create Pinecone index
index = pinecone.Index('pdfbot')

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)

# Define user and bot icons
user_icon = "👩‍💻"
bot_icon = "🤖"

# Initialize conversation history in session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Sidebar menu
with st.sidebar:
    selected_page = option_menu("Main Menu", ['Upload Document', 'Question Answers', 'Indexing and Vector operations'], icons=['cloud-upload', 'question', 'list-task'])

# Display content based on the selected page
if selected_page:
    if selected_page == 'Upload Document':
        st.title("Welcome to Document Uploader")
        st.subheader("Please upload a document.")
        uploaded_file = st.file_uploader("Upload Document", type="pdf")

        if uploaded_file is not None:
            with st.spinner("Uploading..."):
                pdf_content = uploaded_file.read()
                pdf_document = fitz.open("pdf", pdf_content)
                book_texts = [page.get_text() for page in pdf_document]
                pdf_document.close()

                unique_texts = list(set(book_texts))

                # Create vectors using Pinecone
                book_docsearch = Pinecone.from_texts(unique_texts, embeddings, index_name="pdfbot")

            st.success("Document uploaded successfully")

        else:
            st.info("Tip: Supported file formats include PDF.")

    elif selected_page == 'Question Answers':
        st.header("Question Answers")

        # Display chat history
        st.subheader("Chat History")

        for item in st.session_state.chat_history:
            st.markdown(f"{user_icon} **User:** {item['question']}")
            st.markdown(f"{bot_icon} **Bot:** {item['answer']}")

        # User input 
        st.markdown("---")
        st.markdown("**Ask me anything** 🤔")
        user_question = st.text_input(" ", key='user_input', max_chars=500)

        if st.button("Ask", key='ask_button'):
            if user_question:

                # Perform similarity search using Pinecone
                unique_texts = []
                # Use global book_docsearch variable
                book_docsearch = Pinecone.from_texts(unique_texts, embeddings, index_name="pdfbot")
                docs = book_docsearch.similarity_search(user_question)

                # Load QA chain and run it with the retrieved documents
                llm = OpenAI(temperature=0, openai_api_key=openai_api_key)
                chain = load_qa_chain(llm, chain_type="stuff")
                answer = chain.run(input_documents=docs, question=user_question)

                # Save the question-answer pair in session state
                st.session_state.chat_history.append({'question': user_question, 'answer': answer})
                # Response
                st.markdown(f"{bot_icon} **Bot:** {answer}")
                

    elif selected_page == 'Indexing and Vector operations':
        st.header("Indexing and Vector operations")

        # Display chat history
        st.subheader("Chat History")
        for item in st.session_state.chat_history:
            st.markdown(f"{user_icon} **User:** {item['question']}", unsafe_allow_html=True)
            st.markdown(f"{bot_icon} **Bot:** {item['answer']}", unsafe_allow_html=True)
            st.markdown("---")

        action = st.selectbox("Select an action", ['List Indexes', 'Create Index', 'Delete Index', 'Delete Vector', 'Fetch Vector'])

        if action == 'List Indexes':
            indexes = pinecone.list_indexes()
            st.markdown(f"Active indexes: {indexes}")

        elif action == 'Create Index':
            index_name = st.text_input("Index name")
            dimension = st.number_input("Dimension")

            if st.button("Create Index"):
                try:
                    # Convert dimension to integer
                    dimension = int(dimension)
                    pinecone.create_index(index_name, dimension=dimension)
                    st.success(f"Index '{index_name}' created successfully")
                except Exception as e:
                    st.error(f"Failed to create index '{index_name}': {str(e)}")

        elif action == "Delete Index":
            index_name_to_delete = st.text_input("Enter index name to delete")

            if st.button("Delete Index"):
                try:
                    pinecone.delete_index(index_name_to_delete)
                    st.success(f"Index '{index_name_to_delete}' deleted successfully")
                except Exception as e:
                    st.error(f"Failed to delete index '{index_name_to_delete}': {str(e)}")

        elif action == 'Fetch Vector':
            ids_to_fetch = st.text_input("Enter vector IDs to fetch")

            if st.button("Fetch Vector"):
                if ids_to_fetch:
                    ids_to_fetch_list = ids_to_fetch.split(",")

                try:
                    # Fetch vector with the specified IDs
                    fetch_response = index.fetch(ids=ids_to_fetch_list)

                    # Check if fetch_response is not None and has the expected structure
                    if fetch_response is not None and 'vectors' in fetch_response:
                        # Access the 'text' value from the first vector in the response
                        text = fetch_response['vectors'][ids_to_fetch_list[0]]['metadata'].get('text')

                        # Display the 'text' value
                        if text is not None:
                            st.markdown(f"Text: {text}")
                        else:
                            st.warning("Metadata 'text' not found for the specified vector ID.")
                    else:
                        st.error("Failed to fetch vector or unexpected response structure.")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

        elif action == 'Delete Vector':
            ids_to_delete = st.text_input("Enter vector IDs to delete", "")

            if st.button("Delete Vector"):
                if ids_to_delete:
                    ids_to_delete_list = ids_to_delete.split(",")

                try:
                    # Delete vector with the specified IDs
                    delete_response = index.delete(ids=ids_to_delete_list)

                    # Display success message
                    st.success(f"Vector deleted successfully")
                except Exception as e:
                    st.error(f"Failed to delete vector: {str(e)}")
                else:
                    st.error("Please enter valid vector IDs")
