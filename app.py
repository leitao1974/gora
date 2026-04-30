import streamlit as st
import google.generativeai as genai
import pandas as pd
import numpy as np
import sys
import os
import requests
import matplotlib.pyplot as plt
import plotly.express as px
from io import StringIO
import uuid
import json
import time
from docx import Document
from PIL import Image

# --- 1. Configuração da Página ---
st.set_page_config(page_title="GORA Workspace", layout="wide", initial_sidebar_state="expanded")

# --- 2. Persistência de Dados (Custos e Conversas) ---
# Unificamos tudo num ficheiro para evitar inconsistências
DB_FILE = "gora_database.json"

def carregar_dados():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {
        "total_eur": 0.0, 
        "total_tokens": 0,
        "all_chats": {} 
    }

def salvar_dados(dados):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

# --- 3. CSS Vanguardista ---
st.markdown("""
    <style>
    .stApp { background-color: #F0F2F6; color: #1E1E1E; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 2px solid #E0E0E0; }
    h1, h2, h3 { color: #2E7D32 !important; font-weight: 800 !important; letter-spacing: -1px; }
    .stChatMessage {
        background-color: #FFFFFF !important; border: 2px solid #E0E0E0 !important;
        border-radius: 12px !important; box-shadow: 6px 6px 0px rgba(46, 125, 50, 0.08) !important;
        margin-bottom: 15px; padding: 20px !important;
    }
    .stButton button {
        border-radius: 10px !important; border: 2px solid #2E7D32 !important;
        background-color: #FFFFFF !important; color: #2E7D32 !important;
        font-weight: 800 !important; box-shadow: 4px 4px 0px rgba(46, 125, 50, 0.2);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 4. Funções de Suporte ---
@st.cache_data(ttl=3600)
def obter_taxa_eur_usd():
    try:
        return requests.get("https://open.er-api.com/v6/latest/USD", timeout=5).json()['rates']['EUR']
    except: return 0.92

def calcular_custo_eur(input_tokens, output_tokens, taxa):
    return ((input_tokens / 1e6 * 0.30) + (output_tokens / 1e6 * 1.20)) * taxa

def enviar_para_google(uploaded_file):
    temp_path = f"temp_{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    g_file = genai.upload_file(path=temp_path, display_name=uploaded_file.name)
    while g_file.state.name == "PROCESSING":
        time.sleep(2)
        g_file = genai.get_file(g_file.name)
    os.remove(temp_path)
    return g_file

# --- 5. Inicialização de Estado ---
db = carregar_dados()

if "total_eur" not in st.session_state: 
    st.session_state.total_eur = db["total_eur"]
if "total_tokens_session" not in st.session_state: 
    st.session_state.total_tokens_session = db["total_tokens"]
if "all_chats" not in st.session_state: 
    st.session_state.all_chats = db["all_chats"]
if "current_chat_id" not in st.session_state: 
    st.session_state.current_chat_id = None
if "taxa_cambio" not in st.session_state: 
    st.session_state.taxa_cambio = obter_taxa_eur_usd()
if "lab_globals" not in st.session_state:
    st.session_state.lab_globals = {'pd': pd, 'np': np, 'plt': plt, 'px': px, 'st': st}

# --- 6. Barra Lateral ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/144/artificial-intelligence.png", width=60)
    st.title("GORA Workspace")
    menu = st.radio("Navegação", ["💬 GORA Chat", "💻 GORA Lab"])
    
    st.divider()
    st.write("📈 **Custos Acumulados**")
    st.metric("Total Investido", f"{st.session_state.total_eur:.4f} €")
    st.caption(f"Tokens: {st.session_state.total_tokens_session:,}")
    
    if st.button("Resetar Tudo (Local)"):
        st.session_state.total_eur = 0.0
        st.session_state.total_tokens_session = 0
        st.session_state.all_chats = {}
        salvar_dados({"total_eur": 0.0, "total_tokens": 0, "all_chats": {}})
        st.rerun()

    st.divider()
    st.write("### Histórico de Conversas")
    for cid, data in st.session_state.all_chats.items():
        if st.button(data["title"], key=f"btn_{cid}", use_container_width=True):
            st.session_state.current_chat_id = cid
            st.rerun()

    st.divider()
    api_key = st.secrets.get("GOOGLE_API_KEY", st.text_input("Gemini API Key", type="password"))
    if api_key:
        genai.configure(api_key=api_key)
        model_choice = st.selectbox("Modelo:", ["gemini-2.5-flash", "gemini-1.5-pro"])

# --- 7. Módulo Chat ---
if menu == "💬 GORA Chat":
    if not st.session_state.current_chat_id:
        if st.button("➕ INICIAR NOVA ANÁLISE"):
            nid = str(uuid.uuid4())
            st.session_state.all_chats[nid] = {"title": f"Análise {len(st.session_state.all_chats)+1}", "history": []}
            st.session_state.current_chat_id = nid
            # Guardar imediatamente no ficheiro
            db["all_chats"] = st.session_state.all_chats
            salvar_dados(db)
            st.rerun()
    else:
        chat_context = st.session_state.all_chats[st.session_state.current_chat_id]
        
        # Botão para voltar à lista
        if st.button("⬅ Voltar à lista"):
            st.session_state.current_chat_id = None
            st.rerun()

        st.write(f"### {chat_context['title']}")
        
        for m in chat_context["history"]:
            with st.chat_message(m["role"]): st.markdown(m["parts"][0])

        files = st.file_uploader("Upload de Processos (PDF)", accept_multiple_files=True)
        prompt = st.chat_input("Comando...")

        if prompt:
            with st.chat_message("user"): st.markdown(prompt)
            
            conteudo = [prompt]
            if files:
                with st.spinner("GORA a processar..."):
                    for f in files:
                        if f.type == "application/pdf":
                            conteudo.append(enviar_para_google(f))
                        else:
                            conteudo.append(Image.open(f))

            try:
                m = genai.GenerativeModel(model_choice)
                chat_sess = m.start_chat(history=chat_context["history"])
                response = chat_sess.send_message(conteudo)
                
                # Atualizar Estado e Base de Dados
                u = response.usage_metadata
                custo = calcular_custo_eur(u.prompt_token_count, u.candidates_token_count, st.session_state.taxa_cambio)
                
                st.session_state.total_eur += custo
                st.session_state.total_tokens_session += u.total_token_count
                
                # Adicionar ao histórico
                chat_context["history"].append({"role": "user", "parts": [prompt]})
                chat_context["history"].append({"role": "model", "parts": [response.text]})
                
                # Sincronizar com o ficheiro JSON
                db["total_eur"] = st.session_state.total_eur
                db["total_tokens"] = st.session_state.total_tokens_session
                db["all_chats"] = st.session_state.all_chats
                salvar_dados(db)

                st.chat_message("assistant").markdown(response.text)
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

# --- 8. Módulo Lab ---
elif menu == "💻 GORA Lab":
    st.markdown("## 💻 GORA Python Lab")
    code = st.text_area("Script Python", height=300)
    if st.button("⚡ Executar"):
        try:
            exec(code, st.session_state.lab_globals)
            st.success("Sucesso.")
        except Exception as e: st.error(e)




