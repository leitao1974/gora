import streamlit as st
import google.generativeai as genai
import sys
from io import StringIO

# --- Configuração da API ---
# No Streamlit Cloud, você configurará isso em 'Secrets'
# Localmente, você pode usar st.secrets["GOOGLE_API_KEY"] ou um .env
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Por favor, configure a GOOGLE_API_KEY nos Secrets do Streamlit.")

st.set_page_config(page_title="IA Chat & Lab", layout="wide")

tab1, tab2 = st.tabs(["💬 Gemini Chat", "💻 Python Lab"])

with tab1:
    st.header("Assistente Gemini")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Exibir histórico
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Pergunte algo ao Gemini..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Chamada real para o Gemini
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            
            with st.chat_message("assistant"):
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Erro na API: {e}")

# ... (O código da Tab 2 permanece o mesmo do exemplo anterior)
