import streamlit as st
import os
from groq import Groq
import time
import fitz  # PyMuPDF

st.set_page_config(page_title="PDF Content Extractor & Summarizer", layout="centered")

# Session initialization
if "users" not in st.session_state:
    st.session_state.users = {"admin": "admin123"}
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "show_signup" not in st.session_state:
    st.session_state.show_signup = False
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {}
if "active_chat_id" not in st.session_state:
    new_id = f"chat_{int(time.time())}"
    st.session_state.active_chat_id = new_id
    st.session_state.all_chats[new_id] = []
if "chat_titles" not in st.session_state:
    st.session_state.chat_titles = {chat_id: "Untitled Chat" for chat_id in st.session_state.all_chats.keys()}


# Login and Signup functions
def show_login():
    st.title("PDF Content Extractor Login")
    st.subheader("Please log in to continue")
    login_username = st.text_input("Username")
    login_password = st.text_input("Password", type="password")
    if st.button("Login"):
        if login_username in st.session_state.users and st.session_state.users[login_username] == login_password:
            st.success("Logged in successfully!")
            st.session_state.logged_in = True
            st.session_state.username = login_username
            st.rerun()
        else:
            st.error("Invalid credentials")
    st.markdown("Don't have an account?")
    if st.button("Sign Up"):
        st.session_state.show_signup = True


def show_signup():
    st.title("Sign Up for PDF Content Extractor")
    new_username = st.text_input("Choose a username")
    new_password = st.text_input("Choose a password", type="password")
    if st.button("Create Account"):
        if new_username in st.session_state.users:
            st.error("Username already exists!")
        else:
            st.session_state.users[new_username] = new_password
            st.success("Account created! Please log in.")
            st.session_state.show_signup = False


# Enhanced PDF content extraction with page-wise search
@st.cache_data(show_spinner=False)
def load_pdf_pages(pdf_path="NAAC_SSR_SJBIT.pdf"):
    pages_content = []
    try:
        with fitz.open(pdf_path) as doc:
            for page_num, page in enumerate(doc):
                text = page.get_text().strip()
                if text:  # Only add pages with content
                    pages_content.append({
                        "page_number": page_num + 1,
                        "content": text
                    })
    except Exception as e:
        st.error(f"Error loading PDF: {e}")
        return []
    return pages_content


# Find relevant pages based on user query
def find_relevant_pages(query: str, pages_content: list, max_pages=3):
    query_words = set(query.lower().split())
    page_scores = []

    for page in pages_content:
        content_lower = page["content"].lower()
        # Calculate relevance score based on keyword matches
        score = sum(1 for word in query_words if word in content_lower)

        # Boost score for exact phrase matches
        if query.lower() in content_lower:
            score += 5

        if score > 0:
            page_scores.append({
                "page": page,
                "score": score
            })

    # Sort by relevance score and return top pages
    page_scores.sort(key=lambda x: x["score"], reverse=True)
    return [item["page"] for item in page_scores[:max_pages]]


# Extract and combine content from relevant pages
def extract_relevant_content(query: str, pages_content: list):
    relevant_pages = find_relevant_pages(query, pages_content)

    if not relevant_pages:
        return "No relevant content found in the PDF for your query.", []

    combined_content = ""
    page_numbers = []

    for page in relevant_pages:
        combined_content += f"\n--- Page {page['page_number']} ---\n"
        combined_content += page["content"]
        combined_content += "\n"
        page_numbers.append(page["page_number"])

    return combined_content, page_numbers


# Login logic
if not st.session_state.logged_in:
    if st.session_state.show_signup:
        show_signup()
    else:
        show_login()
    st.stop()

# Sidebar
st.sidebar.title("PDF Content Extractor")
st.sidebar.markdown("User: " + st.session_state.username)

if st.sidebar.button("New Chat"):
    new_id = f"chat_{int(time.time())}"
    st.session_state.active_chat_id = new_id
    st.session_state.all_chats[new_id] = []
    st.session_state.chat_titles[new_id] = "Untitled Chat"
    st.rerun()

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("Settings")
max_tokens = st.sidebar.slider("Max Tokens", 256, 2048, 1024, step=128)
summary_type = st.sidebar.selectbox(
    "Summary Type",
    ["Brief Summary", "Detailed Summary", "Key Points", "Question Answer"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("Chat History")
for chat_id in list(st.session_state.all_chats.keys())[::-1]:
    current_title = st.session_state.chat_titles.get(chat_id, "Untitled Chat")
    col1, col2 = st.sidebar.columns([0.8, 0.2])
    if col1.button(f"{current_title}", key=chat_id):
        st.session_state.active_chat_id = chat_id
        st.rerun()
    if col2.button("🗑️", key=f"delete_{chat_id}"):
        del st.session_state.all_chats[chat_id]
        del st.session_state.chat_titles[chat_id]
        if st.session_state.active_chat_id == chat_id:
            if st.session_state.all_chats:
                st.session_state.active_chat_id = next(iter(st.session_state.all_chats))
            else:
                new_id = f"chat_{int(time.time())}"
                st.session_state.active_chat_id = new_id
                st.session_state.all_chats[new_id] = []
                st.session_state.chat_titles[new_id] = "Untitled Chat"
        st.rerun()

with st.sidebar.expander("Rename Current Chat"):
    new_title = st.text_input("Enter new title",
                              value=st.session_state.chat_titles.get(st.session_state.active_chat_id, "Untitled Chat"))
    if st.button("Save Title"):
        st.session_state.chat_titles[st.session_state.active_chat_id] = new_title

# Initialize Groq client
client = Groq(
    api_key="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",
)

# Load PDF pages
with st.spinner("Loading PDF content..."):
    pdf_pages = load_pdf_pages()

if not pdf_pages:
    st.error("Could not load PDF content. Please check if 'NAAC_SSR_SJBIT.pdf' exists in the current directory.")
    st.stop()

# Chat Interface
st.title("Welcome......")
st.caption("Your Personal Thinking Partner!!!")

# Show PDF info
st.info(f"Loaded PDF with {len(pdf_pages)} pages")

active_chat = st.session_state.all_chats[st.session_state.active_chat_id]
for msg in active_chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_query = st.chat_input("Ask about the PDF content...")
if user_query:
    st.chat_message("user").markdown(user_query)
    active_chat.append({"role": "user", "content": user_query})

    with st.chat_message("assistant"):
        with st.spinner("Extracting relevant content and generating summary..."):
            try:
                # Step 1: Extract relevant content from PDF
                relevant_content, page_numbers = extract_relevant_content(user_query, pdf_pages)

                if page_numbers:
                    st.info(f"Found relevant content in pages: {', '.join(map(str, page_numbers))}")

                # Step 2: Create prompt based on summary type
                if summary_type == "Brief Summary":
                    system_prompt = "You are a helpful assistant that provides brief, concise summaries. Extract the key information and present it in 2-3 sentences."
                elif summary_type == "Detailed Summary":
                    system_prompt = "You are a helpful assistant that provides detailed summaries. Include all important points while making the content more readable and organized."
                elif summary_type == "Key Points":
                    system_prompt = "You are a helpful assistant that extracts key points. Present the information as bullet points highlighting the most important aspects."
                else:  # Question Answer
                    system_prompt = "You are a helpful assistant that answers questions based on the provided content. Give a direct, comprehensive answer to the user's question."

                # Step 3: Send to Groq API for summarization
                if "No relevant content found" not in relevant_content:
                    prompt = f"Based on the following PDF content, {summary_type.lower()} for the query: '{user_query}'\n\nContent:\n{relevant_content}\n\nProvide a {summary_type.lower()}:"
                else:
                    prompt = f"I couldn't find relevant content in the PDF for the query: '{user_query}'. Please try with different keywords or check if the content exists in the document."

                response = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[{"role": "system", "content": system_prompt},{"role": "user", "content": prompt}],max_tokens=max_tokens,temperature=0.3
                )

                reply = response.choices[0].message.content

                # Display the summarized response
                st.markdown("###Summary:")
                st.markdown(reply)

                # Add source page information
                if page_numbers:
                    st.markdown(f"**Source Pages:** {', '.join(map(str, page_numbers))}")

                active_chat.append({"role": "assistant", "content": reply})

                # Auto-title the chat based on first query
                if len(active_chat) == 2:
                    first_msg = user_query[:30]
                    st.session_state.chat_titles[st.session_state.active_chat_id] = (
                        first_msg + "..." if len(user_query) > 30 else first_msg
                    )

            except Exception as e:
                error_msg = f"Error processing your request: {e}"
                st.error(error_msg)
                active_chat.append({"role": "assistant", "content": error_msg})

# Instructions
with st.expander("How to use"):
    st.markdown("""
    **How this works:**
    1. **Ask a Question**: Type your question about the PDF content
    2. **Content Extraction**: The system finds relevant pages based on your query
    3. **AI Summary**: Groq AI processes the content and provides a reduced/summarized response

    **Summary Types:**
    - **Brief Summary**: 2-3 sentence overview
    - **Detailed Summary**: Comprehensive but organized summary
    - **Key Points**: Bullet-point format highlighting main aspects
    - **Question Answer**: Direct answer to your specific question

    **Tips for better results:**
    - Use specific keywords related to your topic
    - Ask clear, focused questions
    - Try different summary types for different needs
    """)