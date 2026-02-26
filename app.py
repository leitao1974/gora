import streamlit as st
import google.generativeai as genai
import pandas as pd
import sys
from io import StringIO
import uuid
from PyPDF2 import PdfReader
from docx import Document # Para ficheiros Word
from PIL import Image    # Para Imagens

# --- Configuração da Página ---
st.set_page_config(page_title="Gemini AI Lab", layout="wide")

# --- Inicialização do Estado (Mantido do anterior) ---
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {}
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

# --- Funções de Extração ---
def extrair_texto_pdf(file):
    pdf_reader = PdfReader(file)
    return "".join([page.extract_text() for page in pdf_reader.pages])

def extrair_texto_word(file):
    doc = Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

# --- Interface Sidebar (Mantido do anterior para Histórico e API) ---
with st.sidebar:
    st.title("📂 Histórico")
    if st.button("➕ Nova Conversa", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.all_chats[new_id] = {"title": "Nova Conversa", "messages": []}
        st.session_state.current_chat_id = new_id
        st.rerun()
    
    # ... (Lógica de listagem de chats e API Key igual ao anterior) ...
    api_key = st.secrets.get("GOOGLE_API_KEY", st.text_input("API Key:", type="password"))
    if api_key:
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        selected_model = st.selectbox("Modelo:", models)

# --- Interface Principal ---
tab1, tab2 = st.tabs(["💬 Chat Multimodal", "💻 Python Lab"])

with tab1:
    if st.session_state.current_chat_id and selected_model:
        chat = st.session_state.all_chats[st.session_state.current_chat_id]
        
        for msg in chat["messages"]:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])

        # Upload de Múltiplos Ficheiros (Incluindo Word e Imagem)
        uploaded_files = st.file_uploader(
            "Suba PDFs, Word, Imagens, CSV ou TXT", 
            accept_multiple_files=True,
            type=['pdf', 'docx', 'jpg', 'png', 'jpeg', 'csv', 'txt']
        )

        if prompt := st.chat_input("Pergunte algo sobre os documentos ou imagens..."):
            chat["messages"].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("🤖 O Gemini está a processar tudo..."):
                    try:
                        model = genai.GenerativeModel(selected_model)
                        conteudo_multimodal = [prompt]
                        texto_contexto = ""

                        if uploaded_files:
                            for f in uploaded_files:
                                if f.type.startswith('image/'):
                                    img = Image.open(f)
                                    conteudo_multimodal.append(img)
                                elif f.name.endswith('.docx'):
                                    texto_contexto += f"\n[Word {f.name}]:\n{extrair_texto_word(f)}"
                                elif f.name.endswith('.pdf'):
                                    texto_contexto += f"\n[PDF {f.name}]:\n{extrair_texto_pdf(f)}"
                                elif f.name.endswith('.csv'):
                                    df = pd.read_csv(f)
                                    texto_contexto += f"\n[Dados CSV {f.name}]:\n{df.head().to_string()}"
                                else:
                                    texto_contexto += f"\n[{f.name}]:\n{f.read().decode('utf-8')}"

                        if texto_contexto:
                            conteudo_multimodal.insert(0, f"Contexto extraído:\n{texto_contexto}")

                        # Resposta Multimodal
                        response = model.generate_content(conteudo_multimodal)
                        
                        st.markdown(response.text)
                        chat["messages"].append({"role": "assistant", "content": response.text})
                        
                        if chat["title"] == "Nova Conversa":
                            chat["title"] = prompt[:25] + "..."
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")

# (O código do Tab 2 - Python Lab permanece igual)

