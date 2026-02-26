import streamlit as st
import google.generativeai as genai
import sys
from io import StringIO

st.set_page_config(page_title="Gemini AI Lab", layout="wide")

# --- Barra Lateral para Configurações ---
with st.sidebar:
    st.title("⚙️ Configurações")
    
    # Tenta pegar a chave do Secrets, se não existir, pede ao usuário
    api_key = st.secrets.get("GOOGLE_API_KEY", "")
    if not api_key:
        api_key = st.text_input("Insira sua Google API Key:", type="password")
    
    if api_key:
        genai.configure(api_key=api_key)
        try:
            # Lista apenas os modelos que suportam geração de conteúdo
            available_models = [
                m.name for m in genai.list_models() 
                if 'generateContent' in m.supported_generation_methods
            ]
            selected_model = st.selectbox("Selecione o Modelo:", available_models, index=0)
            st.success("API Conectada!")
        except Exception as e:
            st.error(f"Erro ao listar modelos: {e}")
            selected_model = None
    else:
        st.warning("Aguardando chave API...")
        selected_model = None

# --- Interface Principal ---
tab1, tab2 = st.tabs(["💬 Chat Dinâmico", "💻 Python Lab"])

with tab1:
    if not api_key or not selected_model:
        st.info("Por favor, configure a API Key na barra lateral para começar.")
    else:
        st.header(f"Conversando com: {selected_model.split('/')[-1]}")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("O que vamos criar hoje?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            try:
                model = genai.GenerativeModel(selected_model)
                response = model.generate_content(prompt)
                
                with st.chat_message("assistant"):
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Erro na geração: {e}")

with tab2:
    # O código do interpretador Python (mesmo do exemplo anterior)
    st.header("Python Lab")
    code_input = st.text_area("Célula de Código", height=250, value='print("Testando...")')
    if st.button("▶ Executar"):
        old_stdout = sys.stdout
        redirected_output = sys.stdout = StringIO()
        try:
            exec(code_input)
            st.code(redirected_output.getvalue() or "Executado.")
        except Exception as e:
            st.error(f"Erro: {e}")
        finally:
            sys.stdout = old_stdout
