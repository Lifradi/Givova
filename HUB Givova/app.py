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
    # Se estiver nas Secrets da nuvem, lê de lá
    if "usuarios_hub" in st.secrets:
        return dict(st.secrets["usuarios_hub"])
    
    # Se estiver no computador local, lê do arquivo usuarios.json
    elif os.path.exists('usuarios.json'):
        with open('usuarios.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Padrão caso não ache o arquivo
        return {
            'credentials': {'usernames': {}},
            'cookie': {'name': 'hub_cookie', 'key': 'chave_padrao', 'expiry_days': 1}
        }

config = carregar_configuracao()

# Configuração do Cookie de Sessão
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

# --- TELA DE LOGIN CORRIGIDA PARA VERSÕES NOVAS ---
name, authentication_status, username = authenticator.login(
    fields={'Form name': 'Login - Hub de Automação'}, 
    location='main'
)

if authentication_status == False:
    st.error('❌ Usuário ou senha incorretos.')
elif authentication_status == None:
    st.warning('⚠️ Por favor, digite seu usuário e senha para entrar.')
else:
    # --- ÁREA LOGADA (SÓ APARECE APÓS ACERTAR A SENHA) ---
    authenticator.logout('Sair do Sistema', 'sidebar', key='unique_logout_key')
    
    st.sidebar.markdown(f"👤 **Logado como:** {name}")
    st.sidebar.markdown(f"🔑 **Usuário:** {username}")

    st.title("🛠️ Meu Hub de Scripts e Automações")
    st.write(f"Bem-vindo de volta, {name}! Clique no quadro da ferramenta desejada abaixo:")

    st.markdown("---")

    col1, col2 = st.columns(2)

    def ir_para_romaneios():
        st.switch_page("pages/romaneios.py")

    with col1:
        with st.container(border=True):
            st.subheader("📦 Processador de Romaneios")
            st.write("Lê PDFs de romaneios, cruza com a UF e baixa as notas do Google Drive.")
            
            if st.button("Abrir Romaneios", key="btn_romaneios", use_container_width=True):
                ir_para_romaneios()

    with col2:
        with st.container(border=True):
            st.subheader("🚀 Próximo Roteiro")
            st.write("Espaço reservado para o seu próximo roteiro de automação no futuro.")
            st.caption("Em breve...")
            st.button("Em Breve", key="btn_futuro", disabled=True, use_container_width=True)
