import streamlit as st
import google.generativeai as genai
import pandas as pd
import sys
from io import StringIO
import uuid
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image

# --- 1. Configuração da Página ---
st.set_page_config(page_title="Gemini Interactive Lab", layout="wide", initial_sidebar_state="expanded")

# --- 2. Funções de Extração ---
def extrair_texto_pdf(file):
    try:
        reader = PdfReader(file)
        return "".join([p.extract_text() for p in reader.pages])
    except: return "Erro ao ler PDF."

def extrair_texto_word(file):
    try:
        doc = Document(file)
        return "\n".join([p.text for p in doc.paragraphs])
    except: return "Erro ao ler Word."

# --- 3. Inicialização do Estado ---
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {}
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

# --- 4. Barra Lateral ---
with st.sidebar:
    st.title("🚀 Gemini Interactive")
    menu_opcao = st.radio("Navegação:", ["💬 Chat Bidirecional", "💻 Python Lab"])
    
    st.divider()
    if st.button("➕ Nova Conversa", use_container_width=True):
        nid = str(uuid.uuid4())
        # Agora guardamos o histórico no formato que o Gemini espera: list de dicts {'role', 'parts'}
        st.session_state.all_chats[nid] = {"title": "Nova Conversa", "history": []}
        st.session_state.current_chat_id = nid
        st.rerun()
    
    for cid, data in list(st.session_state.all_chats.items()):
        col1, col2 = st.columns([0.8, 0.2])
        if col1.button(data["title"], key=cid, use_container_width=True):
            st.session_state.current_chat_id = cid
            st.rerun()
        if col2.button("🗑️", key=f"del_{cid}"):
            del st.session_state.all_chats[cid]
            if st.session_state.current_chat_id == cid: st.session_state.current_chat_id = None
            st.rerun()

    st.divider()
    api_key = st.secrets.get("GOOGLE_API_KEY", st.text_input("API Key:", type="password"))
    selected_model = None
    if api_key:
        genai.configure(api_key=api_key)
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            selected_model = st.selectbox("Modelo:", models, index=0)
        except: st.error("Erro na API Key.")

# --- 5. Lógica Principal ---

if menu_opcao == "💬 Chat Bidirecional":
    st.header("Interação com IA")
    
    if not st.session_state.current_chat_id:
        st.info("Crie uma conversa à esquerda.")
    elif not selected_model:
        st.warning("Configure a API Key.")
    else:
        chat_data = st.session_state.all_chats[st.session_state.current_chat_id]
        
        # Exibir histórico (Formatando para o Streamlit)
        for message in chat_data["history"]:
            role = "assistant" if message["role"] == "model" else "user"
            with st.chat_message(role):
                st.markdown(message["parts"][0])

        files = st.file_uploader("Upload de contexto (opcional)", accept_multiple_files=True)

        if prompt := st.chat_input("Escreve a tua mensagem..."):
            # Exibir mensagem do utilizador imediatamente
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Preparar contexto de ficheiros se for a primeira mensagem ou houver novos
            contexto_extra = ""
            if files:
                for f in files:
                    if f.name.endswith('.pdf'): contexto_extra += f"\n[PDF: {f.name}] {extrair_texto_pdf(f)}"
                    elif f.name.endswith('.docx'): contexto_extra += f"\n[Word: {f.name}] {extrair_texto_word(f)}"
                    elif f.name.endswith('.csv'): contexto_extra += f"\n[CSV: {f.name}] {pd.read_csv(f).head().to_string()}"
            
            prompt_final = f"{prompt}\n\n(Contexto adicional: {contexto_extra})" if contexto_extra else prompt

            # --- Lógica de Chat Bidirecional com Gemini ---
            model = genai.GenerativeModel(selected_model)
            # Inicia a sessão com o histórico existente
            chat_session = model.start_chat(history=chat_data["history"])
            
            with st.chat_message("assistant"):
                placeholder = st.empty()
                full_response = ""
                
                with st.spinner("IA a pensar..."):
                    # Streaming para resposta dinâmica
                    response = chat_session.send_message(prompt_final, stream=True)
                    
                    for chunk in response:
                        full_response += chunk.text
                        placeholder.markdown(full_response + "▌") # Efeito de cursor
                    placeholder.markdown(full_response)

            # Guardar no histórico (formato Gemini)
            chat_data["history"].append({"role": "user", "parts": [prompt]})
            chat_data["history"].append({"role": "model", "parts": [full_response]})
            
            if chat_data["title"] == "Nova Conversa":
                chat_data["title"] = prompt[:20] + "..."
                st.rerun()

elif menu_opcao == "💻 Python Lab":
    st.header("Python Lab")
    editor_code = st.text_area("Editor Python:", height=300, value="print('Pronto para testar!')")
    if st.button("▶ Executar"):
        old_stdout = sys.stdout
        sys.stdout = out = StringIO()
        try:
            exec(editor_code, {'pd': pd, 'st': st})
            st.code(out.getvalue())
        except Exception as e: st.error(f"Erro: {e}")
        finally: sys.stdout = old_stdout
