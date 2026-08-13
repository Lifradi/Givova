import json
import os
import streamlit as st
import streamlit_authenticator as stauth

# --- ALTERADO PARA WIDE PARA DAR ESPAÇO AOS CARDS ---
st.set_page_config(
    page_title="Hub de Automação - Acesso Restrito",
    page_icon="🔒",
    layout="wide",
)


# --- CARREGA OS USUÁRIOS DE FORMA EXTERNA ---
def carregar_configuracao():
    if "usuarios_hub" in st.secrets:
        return dict(st.secrets["usuarios_hub"])
    elif os.path.exists("usuarios.json"):
        with open("usuarios.json", "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {
            "credentials": {"usernames": {}},
            "cookie": {
                "name": "hub_cookie",
                "key": "chave_padrao",
                "expiry_days": 1,
            },
        }


config = carregar_configuracao()

cookie_config = {
    "name": "hub_givova_cookie",
    "key": "chave_secreta_super_segura_123",
    "expiry_days": 1,
}

authenticator = stauth.Authenticate(
    config["credentials"],
    cookie_config["name"],
    cookie_config["key"],
    cookie_expiry_days=cookie_config["expiry_days"],
)

# --- TELA DE LOGIN ---
authenticator.login()

authentication_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")
username = st.session_state.get("username")

if authentication_status == False:
    st.error("❌ Usuário ou senha incorretos.")
elif authentication_status == None:
    st.warning("⚠️ Por favor, digite seu usuário e senha para entrar.")
else:
    # --- ÁREA LOGADA ---
    authenticator.logout("Sair do Sistema", "sidebar", key="unique_logout_key")

    st.sidebar.markdown(f"👤 **Logado como:** {name}")
    st.sidebar.markdown(f"🔑 **Usuário:** {username}")

    st.title("🛠️ Meu Hub de Scripts e Automações")
    st.write(f"Bem-vindo de volta, {name}! Escolha a ferramenta desejada abaixo:")

    st.markdown("---")

    def ir_para_romaneios():
        st.switch_page("pages/romaneios.py")

    def ir_para_canhotos():
        st.switch_page("pages/canhotos.py")

    def ir_para_xml():
        st.switch_page("pages/xml_converter.py")

    def ir_para_extrator():
        st.switch_page("pages/extrator_xml.py")

    def ir_para_extrator_faturas():
        st.switch_page("pages/extrator_faturas.py")

    # --- ORGANIZAÇÃO EM GRADE ---
    # Linha 1
    linha1_col1, linha1_col2 = st.columns(2)

    with linha1_col1:
        with st.container(border=True):
            st.subheader("📦 Romaneios")
            st.write("Filtra PDFs e baixa notas do Google Drive de forma automática.")
            if st.button("Abrir Ferramenta", key="btn_romaneios", use_container_width=True):
                ir_para_romaneios()

    with linha1_col2:
        with st.container(border=True):
            st.subheader("📄 Canhotos")
            st.write("Lê imagens de canhotos assinados e gera relatório em Excel.")
            if st.button("Abrir Ferramenta", key="btn_canhotos", use_container_width=True):
                ir_para_canhotos()

    st.write("")  # Pequeno espaçamento vertical entre as linhas

    # Linha 2
    linha2_col1, linha2_col2 = st.columns(2)

    with linha2_col1:
        with st.container(border=True):
            st.subheader("⚡ PDF para XML")
            st.write("Converte arquivos em formato PDF em pacotes organizados de XMLs.")
            if st.button("Abrir Ferramenta", key="btn_xml", use_container_width=True):
                ir_para_xml()

    with linha2_col2:
        with st.container(border=True):
            st.subheader("📊 Separador de Cargas")
            st.write("Lê lotes de arquivos XMLs e faz a separação automática por número de carga.")
            if st.button("Abrir Ferramenta", key="btn_extrator", use_container_width=True):
                ir_para_extrator()

    st.write("")  # Pequeno espaçamento vertical entre as linhas

    # Linha 3 (Nova ferramenta adicionada aqui)
    linha3_col1, linha3_col2 = st.columns(2)

    with linha3_col1:
        with st.container(border=True):
            st.subheader("📑 Extrator de Faturas")
            st.write("Lê PDFs de faturas em lote e gera planilha de controle formatada.")
            if st.button("Abrir Ferramenta", key="btn_faturas", use_container_width=True):
                ir_para_extrator_faturas()
    
    with linha3_col2:
        # Coluna vazia para manter o alinhamento do layout, pronta para o próximo script!
        st.empty()
