import io
import json
import os
import re
import zipfile
import streamlit as st
import streamlit_authenticator as stauth

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Organizador de XMLs por Carga", page_icon="📁", layout="centered"
)

# --- CARREGA OS USUÁRIOS PARA VALIDAÇÃO DIRETA ---
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

# Tenta carregar o estado da sessão de login
authentication_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")
username = st.session_state.get("username")

# --- BLOQUEIO DE SEGURANÇA SE NÃO ESTIVER LOGADO ---
if not authentication_status:
  st.error(
      "🔒 Acesso Negado! Por favor, faça o login na página principal do Hub"
      " primeiro."
  )
  if st.button("Ir para o Login"):
    st.switch_page("app.py")
  st.stop()

# Se estiver logado, exibe os elementos da barra lateral
authenticator.logout("Sair do Sistema", "sidebar", key="logout_xmls")
st.sidebar.markdown(f"👤 **Logado como:** {name}")

# --- CORPO DO SISTEMA ---
st.title("📁 Organizador de XMLs por Carga")
st.write(
    "Envie seus arquivos XMLs de notas/romaneios. O sistema lê o conteúdo, "
    "separa-os automaticamente por número de carga e gera um arquivo ZIP organizado."
)

# Componente para upload de múltiplos arquivos XML
arquivos_xml = st.file_uploader(
    "📂 Envie os arquivos XML", type=["xml"], accept_multiple_files=True
)

if arquivos_xml:
  if st.button("🚀 Processar e Organizar XMLs"):
    padrao_carga = re.compile(r"Carga:\s*(\d+)", re.IGNORECASE)

    contador_sucesso = 0
    contador_erro = 0
    cargas_encontradas = {}  # Dicionário para armazenar {numero_carga: {nome_arquivo: bytes}}

    with st.spinner("Processando e organizando os arquivos..."):
      for arquivo in arquivos_xml:
        nome_arquivo = arquivo.name
        try:
          bytes_conteudo = arquivo.read()
          conteudo_texto = bytes_conteudo.decode("utf-8", errors="ignore")
          match = padrao_carga.search(conteudo_texto)

          if match:
            numero_carga = match.group(1)

            if numero_carga not in cargas_encontradas:
              cargas_encontradas[numero_carga] = {}

            cargas_encontradas[numero_carga][nome_arquivo] = bytes_conteudo
            contador_sucesso += 1
          else:
            contador_erro += 1

        except Exception as e:
          contador_erro += 1

    # Exibe métricas do processamento
    col1, col2 = st.columns(2)
    col1.metric("XMLs Organizados com Sucesso", contador_sucesso)
    col2.metric("XMLs sem Carga / Erros", contador_erro)

    if contador_sucesso > 0:
      zip_buffer = io.BytesIO()

      with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for carga, arquivos_dict in cargas_encontradas.items():
          for nome_arq, conteudo_bytes in arquivos_dict.items():
            caminho_no_zip = f"carga {carga}/{nome_arq}"
            zipf.writestr(caminho_no_zip, conteudo_bytes)

      zip_buffer.seek(0)

      st.success("✅ Organização concluída com sucesso!")

      st.download_button(
          label="📥 Baixar ZIP Organizado por Cargas",
          data=zip_buffer,
          file_name="xmls_organizados_por_carga.zip",
          mime="application/zip",
          key="btn_download_xmls",
      )
    else:
      st.warning(
          "⚠️ Nenhum arquivo continha uma 'Carga' válida para ser organizado."
      )
