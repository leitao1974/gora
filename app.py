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
st.set_page_config(page_title="Gemini Expert Lab", layout="wide", initial_sidebar_state="expanded")

# --- 2. CSS para Melhorar o Layout ---
st.markdown("""
    <style>
    /* Estilo das mensagens de chat */
    .stChatMessage {
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 10px;
    }
    /* Estilo dos botões de sugestão */
    .stButton button {
        border-radius: 20px;
        border: 1px solid #4CAF50;
        background-color: transparent;
        color: #4CAF50;
        transition: 0.3s;
    }
    .stButton button:hover {
        background-color: #4CAF50;
        color: white;
    }
    /* Alinhamento do Lab */
    .code-output {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Funções de Extração ---
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

# --- 4. Inicialização do Estado ---
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {}
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
if "suggestions" not in st.session_state:
    st.session_state.suggestions = []

# --- 5. Barra Lateral ---
with st.sidebar:
    st.title("🤖 AI Workspace")
    menu_opcao = st.radio("Módulo:", ["💬 Assistente Inteligente", "💻 Laboratório Python"])
    
    st.divider()
    if st.button("➕ Nova Conversa", use_container_width=True):
        nid = str(uuid.uuid4())
        st.session_state.all_chats[nid] = {"title": "Nova Conversa", "history": []}
        st.session_state.current_chat_id = nid
        st.session_state.suggestions = []
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
            selected_model = st.selectbox("Modelo:", models)
        except: st.error("Erro na API.")

# --- 6. Módulo: Chat Inteligente ---
if menu_opcao == "💬 Assistente Inteligente":
    st.subheader("Conversa Dinâmica")
    
    if not st.session_state.current_chat_id:
        st.info("Inicie uma conversa para começar.")
    elif selected_model:
        chat_data = st.session_state.all_chats[st.session_state.current_chat_id]
        
        # Histórico
        for message in chat_data["history"]:
            role = "assistant" if message["role"] == "model" else "user"
            with st.chat_message(role): st.markdown(message["parts"][0])

        # Sugestões de Perguntas (Botões Clicáveis)
        if st.session_state.suggestions:
            st.write("💡 *Sugestões:*")
            cols = st.columns(len(st.session_state.suggestions))
            for i, sug in enumerate(st.session_state.suggestions):
                if cols[i].button(sug, key=f"sug_{i}"):
                    # Se clicar, define o prompt como a sugestão
                    st.session_state.prompt_input = sug
                    st.rerun()

        files = st.file_uploader("Contexto adicional", accept_multiple_files=True)
        
        prompt = st.chat_input("Como posso ajudar?")
        # Lógica para aceitar clique na sugestão
        if "prompt_input" in st.session_state:
            prompt = st.session_state.pop("prompt_input")

        if prompt:
            with st.chat_message("user"): st.markdown(prompt)
            
            contexto = ""
            for f in files:
                if f.name.endswith('.pdf'): contexto += extrair_texto_pdf(f)
                elif f.name.endswith('.docx'): contexto += extrair_texto_word(f)
                elif f.name.endswith('.csv'): contexto += pd.read_csv(f).head().to_string()

            # Chat Session
            model = genai.GenerativeModel(selected_model)
            chat_session = model.start_chat(history=chat_data["history"])
            
            with st.chat_message("assistant"):
                with st.spinner("A processar..."):
                    # Pedimos a resposta + sugestões no mesmo prompt para poupar tempo
                    full_prompt = f"{prompt}\n\nContexto: {contexto}\n\nNo final da tua resposta, adiciona uma linha começando com 'SUGESTÕES:' seguida de 3 perguntas curtas separadas por vírgula que eu possa fazer a seguir."
                    
                    response = chat_session.send_message(full_prompt)
                    
                    # Separar resposta de sugestões
                    text_parts = response.text.split("SUGESTÕES:")
                    resposta_principal = text_parts[0]
                    novas_sugestoes = text_parts[1].split(",") if len(text_parts) > 1 else []
                    
                    st.markdown(resposta_principal)
                    st.session_state.suggestions = [s.strip() for s in novas_sugestoes][:3]

            chat_data["history"].append({"role": "user", "parts": [prompt]})
            chat_data["history"].append({"role": "model", "parts": [resposta_principal]})
            
            if chat_data["title"] == "Nova Conversa":
                chat_data["title"] = prompt[:20] + "..."
            st.rerun()

# --- 7. Módulo: Laboratório Python (Layout Melhorado) ---
elif menu_opcao == "💻 Laboratório Python":
    st.subheader("Python Lab Environment")
    
    col_code, col_out = st.columns([1, 1], gap="large")
    
    with col_code:
        st.write("📝 **Editor**")
        code = st.text_area("Insira o código:", height=400, value="import pandas as pd\nprint('Olá!')")
        c1, c2 = st.columns(2)
        exec_btn = c1.button("▶ Executar", use_container_width=True)
        c2.download_button("📥 Exportar .py", code, file_name="script.py", use_container_width=True)

    with col_out:
        st.write("📊 **Resultado**")
        if exec_btn:
            old_stdout = sys.stdout
            sys.stdout = out = StringIO()
            try:
                exec(code, {'pd': pd, 'st': st})
                st.code(out.getvalue())
            except Exception as e: st.error(f"Erro: {e}")
            finally: sys.stdout = old_stdout
        else:
            st.info("O output aparecerá aqui após a execução.")
