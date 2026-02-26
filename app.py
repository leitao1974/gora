import streamlit as st
import google.generativeai as genai
import pandas as pd
import sys
from io import StringIO
import uuid
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image

# --- 1. Configuração da Página (Deve ser o primeiro comando) ---
st.set_page_config(page_title="Gemini AI Lab", layout="wide", initial_sidebar_state="expanded")

# --- 2. CSS Robusto para Fixar Tabs (Correção Definitiva) ---
st.markdown("""
    <style>
    /* Fixar a barra de abas no topo absoluto */
    div[data-testid="stTabs"] > div:first-child {
        position: fixed !important;
        top: 0px !important;
        background-color: white !important;
        z-index: 9999 !important;
        width: 100% !important;
        border-bottom: 2px solid #4CAF50 !important;
        padding: 45px 20px 0px 20px !important; /* Espaço para a barra de sistema do Streamlit */
    }
    /* Empurrar o conteúdo das abas para baixo para não ser tapado */
    div[data-testid="stTabs"] > div:nth-child(2) {
        margin-top: 100px !important;
    }
    /* Estética dos botões e inputs */
    .stDownloadButton, .stButton {
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Funções de Extração de Documentos ---
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

# --- 4. Gestão de Estado (Sessões de Chat) ---
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {}
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

# --- 5. Barra Lateral (Histórico e Configurações) ---
with st.sidebar:
    st.title("📂 Conversas")
    if st.button("➕ Nova Conversa", use_container_width=True):
        nid = str(uuid.uuid4())
        st.session_state.all_chats[nid] = {"title": "Nova Conversa", "messages": []}
        st.session_state.current_chat_id = nid
        st.rerun()
    
    # Listagem de chats guardados
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
    
    # Chave API (Prioriza Secrets do Streamlit Cloud)
    api_key = st.secrets.get("GOOGLE_API_KEY", "")
    if not api_key:
        api_key = st.text_input("Introduza a Google API Key:", type="password")

    selected_model = None
    if api_key:
        genai.configure(api_key=api_key)
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            selected_model = st.selectbox("Modelo Gemini:", models)
        except: st.error("Chave API inválida ou erro de conexão.")

# --- 6. Interface de Abas Principal ---
tab1, tab2 = st.tabs(["💬 Chat Dinâmico", "💻 Python Lab"])

# --- ABA 1: CHAT IA ---
with tab1:
    if not st.session_state.current_chat_id:
        st.info("Crie uma conversa na barra lateral para começar.")
    elif not selected_model:
        st.warning("Configure a API Key para ativar o Chat.")
    else:
        chat_session = st.session_state.all_chats[st.session_state.current_chat_id]
        
        # Exibir Histórico
        for msg in chat_session["messages"]:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])

        # Upload de Ficheiros (Vários tipos ao mesmo tempo)
        files = st.file_uploader("Upload: PDF, Word, Imagem, CSV, TXT", accept_multiple_files=True)

        if prompt := st.chat_input("Pergunte ao Gemini..."):
            chat_session["messages"].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("🤖 Analisando conteúdo..."):
                    try:
                        model = genai.GenerativeModel(selected_model)
                        payload = [prompt]
                        contexto = ""
                        
                        for f in files:
                            if f.type.startswith('image/'):
                                payload.append(Image.open(f))
                            elif f.name.endswith('.pdf'):
                                contexto += f"\n[PDF: {f.name}]\n{extrair_texto_pdf(f)}"
                            elif f.name.endswith('.docx'):
                                contexto += f"\n[Word: {f.name}]\n{extrair_texto_word(f)}"
                            elif f.name.endswith('.csv'):
                                df = pd.read_csv(f)
                                contexto += f"\n[CSV: {f.name}]\n{df.head().to_string()}"
                        
                        if contexto: payload.insert(0, f"Contexto:\n{contexto}")
                        
                        resp = model.generate_content(payload)
                        st.markdown(resp.text)
                        chat_session["messages"].append({"role": "assistant", "content": resp.text})
                        
                        # Renomear chat se for o início
                        if chat_session["title"] == "Nova Conversa":
                            chat_session["title"] = prompt[:25] + "..."
                            st.rerun()
                    except Exception as e: st.error(f"Erro na IA: {e}")

# --- ABA 2: PYTHON LAB ---
with tab2:
    st.header("Python Lab")
    st.caption("Teste scripts, processe dados e visualize resultados.")
    
    code_area = st.text_area("Editor Python:", height=300, 
                            value="# Escreva o seu código aqui\nimport pandas as pd\nprint('Lab pronto!')")
    
    c1, c2 = st.columns(2)
    with c1:
        run_btn = st.button("▶ Executar Código", use_container_width=True)
    with c2:
        st.download_button(
            label="📥 Descarregar Script (.py)",
            data=code_area,
            file_name="script_gerado.py",
            mime="text/x-python",
            use_container_width=True
        )

    if run_btn:
        old_stdout = sys.stdout
        sys.stdout = out = StringIO()
        try:
            # Contexto de execução com bibliotecas comuns disponíveis
            exec(code_area, {'pd': pd, 'st': st, 'genai': genai, 'plt': None})
            st.subheader("Console Output:")
            st.code(out.getvalue() if out.getvalue() else "Executado com sucesso (sem output).")
        except Exception as e:
            st.error(f"Erro de Execução: {e}")
        finally:
            sys.stdout = old_stdout


