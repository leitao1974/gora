import streamlit as st
import google.generativeai as genai
import pandas as pd
import sys
from io import StringIO
import uuid
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image

# --- Configuração da Página ---
st.set_page_config(page_title="Gemini AI Lab", layout="wide")

# --- CSS FIXO (Tabs no Topo) ---
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] {
        position: fixed;
        top: 0;
        background-color: white;
        z-index: 1000;
        width: 100%;
        border-bottom: 2px solid #4CAF50;
        padding: 10px 20px 0px 20px;
    }
    .stTabs [data-baseweb="tab-panel"] {
        margin-top: 60px;
    }
    /* Estilo para o botão de download */
    .stDownloadButton {
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Funções de Extração ---
def extrair_texto_pdf(file):
    try:
        return "".join([p.extract_text() for p in PdfReader(file).pages])
    except: return "Erro ao ler PDF."

def extrair_texto_word(file):
    try:
        return "\n".join([p.text for p in Document(file).paragraphs])
    except: return "Erro ao ler Word."

# --- Gestão de Estado e Sidebar ---
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {}
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

with st.sidebar:
    st.title("📂 Histórico")
    if st.button("➕ Nova Conversa", use_container_width=True):
        nid = str(uuid.uuid4())
        st.session_state.all_chats[nid] = {"title": "Nova Conversa", "messages": []}
        st.session_state.current_chat_id = nid
        st.rerun()
    
    for cid, data in list(st.session_state.all_chats.items()):
        col1, col2 = st.columns([0.8, 0.2])
        if col1.button(data["title"], key=cid, use_container_width=True):
            st.session_state.current_chat_id = cid
            st.rerun()
        if col2.button("🗑️", key=f"d_{cid}"):
            del st.session_state.all_chats[cid]
            if st.session_state.current_chat_id == cid: st.session_state.current_chat_id = None
            st.rerun()

    st.divider()
    api_key = st.secrets.get("GOOGLE_API_KEY", "")
    if not api_key:
        api_key = st.text_input("Introduza a Google API Key:", type="password")

    selected_model = None
    if api_key:
        genai.configure(api_key=api_key)
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            selected_model = st.selectbox("Modelo Gemini:", models)
        except: st.error("Erro na API Key.")

# --- Interface Principal ---
tab1, tab2 = st.tabs(["💬 Chat Multimodal", "💻 Python Lab"])

with tab1:
    if st.session_state.current_chat_id and selected_model:
        chat = st.session_state.all_chats[st.session_state.current_chat_id]
        
        for msg in chat["messages"]:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])

        files = st.file_uploader("Upload: PDF, Word, Imagem, CSV", accept_multiple_files=True)

        if prompt := st.chat_input("Pergunte ao Gemini..."):
            chat["messages"].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("🤖 Analisando ficheiros e gerando resposta..."):
                    try:
                        model = genai.GenerativeModel(selected_model)
                        conteudo = [prompt]
                        contexto_texto = ""
                        
                        for f in files:
                            if f.type.startswith('image/'):
                                conteudo.append(Image.open(f))
                            elif f.name.endswith('.pdf'):
                                contexto_texto += f"\n[PDF {f.name}]:\n{extrair_texto_pdf(f)}"
                            elif f.name.endswith('.docx'):
                                contexto_texto += f"\n[Word {f.name}]:\n{extrair_texto_word(f)}"
                            elif f.name.endswith('.csv'):
                                contexto_texto += f"\n[CSV {f.name}]:\n{pd.read_csv(f).head().to_string()}"
                        
                        if contexto_texto:
                            conteudo.insert(0, f"Contexto extraído:\n{contexto_texto}")
                        
                        resp = model.generate_content(conteudo)
                        st.markdown(resp.text)
                        chat["messages"].append({"role": "assistant", "content": resp.text})
                        
                        if chat["title"] == "Nova Conversa":
                            chat["title"] = prompt[:25] + "..."
                            st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")

with tab2:
    st.header("Python Lab")
    st.write("Escreva e teste o seu código aqui.")
    
    code_input = st.text_area("Célula de Código Python:", height=300, 
                             value="# Exemplo: \nimport pandas as pd\nprint('Ambiente pronto!')")
    
    col_run, col_dl = st.columns([1, 1])
    
    with col_run:
        btn_run = st.button("▶ Executar Código", use_container_width=True)
    
    with col_dl:
        st.download_button(
            label="📥 Descarregar Script (.py)",
            data=code_input,
            file_name="meu_script.py",
            mime="text/x-python",
            use_container_width=True
        )

    if btn_run:
        old_stdout = sys.stdout
        sys.stdout = out = StringIO()
        try:
            # Executa com acesso a bibliotecas comuns
            exec(code_input, {'pd': pd, 'st': st, 'genai': genai, 'plt': None})
            st.subheader("Saída (Console):")
            result = out.getvalue()
            if result:
                st.code(result)
            else:
                st.info("Código executado sem saída de texto.")
        except Exception as e:
            st.error(f"Erro de Execução: {e}")
        finally:
            sys.stdout = old_stdout


