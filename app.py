import streamlit as st
import google.generativeai as genai
import pandas as pd
import sys
from io import StringIO
import uuid # Para gerar IDs únicos para cada conversa

# --- Configuração da Página ---
st.set_page_config(page_title="Gemini AI Lab", layout="wide")

# --- Inicialização do Histórico Permanente ---
if "all_chats" not in st.session_state:
    st.session_state.all_chats = {} # Estrutura: {id: {"title": str, "messages": list, "files": list}}

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

# --- CSS para Fixar as Tabs ---
st.markdown("""
    <style>
    div[data-testid="stTabs"] > div:first-child {
        position: fixed; top: 60px; background-color: white; z-index: 999;
        width: 100%; padding: 10px 0; border-bottom: 1px solid #ddd;
    }
    div[data-testid="stTabs"] > div:nth-child(2) { margin-top: 80px; }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar: Gestão de Conversas ---
with st.sidebar:
    st.title("📂 Conversas")
    
    if st.button("➕ Nova Conversa", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.all_chats[new_id] = {"title": f"Chat {len(st.session_state.all_chats)+1}", "messages": [], "files": []}
        st.session_state.current_chat_id = new_id
        st.rerun()

    st.divider()
    
    # Listar conversas guardadas
    for chat_id, chat_data in st.session_state.all_chats.items():
        col1, col2 = st.columns([0.8, 0.2])
        if col1.button(chat_data["title"], key=chat_id, use_container_width=True):
            st.session_state.current_chat_id = chat_id
            st.rerun()
        if col2.button("🗑️", key=f"del_{chat_id}"):
            del st.session_state.all_chats[chat_id]
            if st.session_state.current_chat_id == chat_id:
                st.session_state.current_chat_id = None
            st.rerun()

    st.divider()
    st.title("⚙️ API Config")
    api_key = st.secrets.get("GOOGLE_API_KEY", st.text_input("API Key:", type="password"))
    # ... (restante da lógica de config da API permanece igual)

# --- Interface Principal ---
tab1, tab2 = st.tabs(["💬 Chat Multimodal", "💻 Python Lab"])

with tab1:
    if not st.session_state.current_chat_id:
        st.info("Clique em '➕ Nova Conversa' na barra lateral para começar.")
    else:
        current_chat = st.session_state.all_chats[st.session_state.current_chat_id]
        
        # Título Dinâmico do Chat
        st.subheader(current_chat["title"])

        # Exibir Mensagens da Conversa Atual
        for message in current_chat["messages"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Upload de Ficheiros
        uploaded_files = st.file_uploader("📂 Ficheiros", accept_multiple_files=True, key=f"file_{st.session_state.current_chat_id}")
        
        if prompt := st.chat_input("Pergunte ao Gemini..."):
            # Guardar no histórico da sessão específica
            current_chat["messages"].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("🤖 Analisando..."):
                    # (Aqui entra a lógica de API do Gemini que já construímos anteriormente)
                    # Exemplo simplificado:
                    response_text = f"Resposta simulada para: {prompt}" 
                    st.markdown(response_text)
                    current_chat["messages"].append({"role": "assistant", "content": response_text})
                    
                    # Atualizar título do chat com a primeira pergunta
                    if current_chat["title"].startswith("Chat "):
                        current_chat["title"] = prompt[:30] + "..."
                        st.rerun()

with tab2:
    # O Python Lab permanece funcional e pode usar os ficheiros carregados no chat atual
    st.header("Python Lab")
    # ... (lógica do exec() que já fizemos)

