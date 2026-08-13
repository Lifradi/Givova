import json
import os
import streamlit as st
import streamlit_authenticator as stauth

st.set_page_config(
    page_title="Hub de Automação - Acesso Restrito",
    page_icon="🔒",
    layout="centered"
)

# --- CARREGA OS USUÁRIOS DE FORMA EXTERNA ---
def carregar_configuracao():
    if "usuarios_hub" in st.secrets:
        return dict(st.secrets["usuarios_hub"])
    elif os.path.exists('usuarios.json'):
        with open('usuarios.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {
            'credentials': {'usernames': {}},
            'cookie': {'name': 'hub_cookie', 'key': 'chave_padrao', 'expiry_days': 1}
        }

config = carregar_configuracao()

cookie_config = {
    'name': 'hub_givova_cookie',
    'key': 'chave_secreta_super_segura_123',
    'expiry_days': 1
}

authenticator = stauth.Authenticate(
    config['credentials'],
    cookie_config['name'],
    cookie_config['key'],
    cookie_expiry_days=cookie_config['expiry_days']
)

# --- TELA DE LOGIN ---
authenticator.login()

authentication_status = st.session_state.get('authentication_status')
name = st.session_state.get('name')
username = st.session_state.get('username')

if authentication_status == False:
    st.error('❌ Usuário ou senha incorretos.')
elif authentication_status == None:
    st.warning('⚠️ Por favor, digite seu usuário e senha para entrar.')
else:
    # --- ÁREA LOGADA ---
    authenticator.logout('Sair do Sistema', 'sidebar', key='unique_logout_key')
    
    st.sidebar.markdown(f"👤 **Logado como:** {name}")
    st.sidebar.markdown(f"🔑 **Usuário:** {username}")

    st.title("🛠️ Meu Hub de Scripts e Automações")
    st.write(f"Bem-vindo de volta, {name}! Escolha a ferramenta desejada abaixo:")

    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)

    def ir_para_romaneios():
        st.switch_page("pages/romaneios.py")

    def ir_para_canhotos():
        st.switch_page("pages/canhotos.py")

    def ir_para_xml():
        st.switch_page("pages/xml_converter.py")

    def ir_para_extrator():
        st.switch_page("pages/extrator_xml.py")

    with col1:
        with st.container(border=True):
            st.subheader("📦 Romaneios")
            st.write("Filtra PDFs e baixa notas do Google Drive.")
            if st.button("Abrir", key="btn_romaneios", use_container_width=True):
                ir_para_romaneios()

    with col2:
        with st.container(border=True):
            st.subheader("📄 Canhotos")
            st.write("Lê imagens e gera relatório Excel.")
            if st.button("Abrir", key="btn_canhotos", use_container_width=True):
                ir_para_canhotos()

    with col3:
        with st.container(border=True):
            st.subheader("⚡ PDF para XML")
            st.write("Converte PDFs em pacotes de XMLs.")
            if st.button("Abrir", key="btn_xml", use_container_width=True):
                ir_para_xml()

    with col4:
        with st.container(border=True):
            st.subheader("📊 Separador de Cargas")
            st.write("Lê XMLs e separa por número de carga.")
            if st.button("Abrir", key="btn_extrator", use_container_width=True):
                ir_para_extrator()
