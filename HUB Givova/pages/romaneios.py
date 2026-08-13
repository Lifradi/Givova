import io
import json
import os
import re
import zipfile
import PyPDF2
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import streamlit as st
import streamlit_authenticator as stauth

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Tratamento de Romaneios", page_icon="📦", layout="centered"
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

# Se estiver logado, exibe os elementos da barra lateral e o sistema normal
authenticator.logout("Sair do Sistema", "sidebar", key="logout_romaneios")
st.sidebar.markdown(f"👤 **Logado como:** {name}")

st.title("📦 Sistema de Tratamento e Baixa de Romaneios por UF")
st.write(
    "O sistema lê a nota fiscal e a unidade destino do PDF para baixar apenas"
    " os arquivos correspondentes daquela UF."
)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def extrair_dados_do_pdf(arquivo_bytes):
  itens_extraidos = []
  try:
    leitor = PyPDF2.PdfReader(io.BytesIO(arquivo_bytes))
    for pagina in leitor.pages:
      texto = pagina.extract_text()
      if texto:
        linhas = texto.split("\n")
        for linha in linhas:
          matches_nf = re.findall(
              r"(?<![\d.,/-])\b[1-9]\d{3,8}\b(?![\d.,/-])", linha
          )
          if matches_nf:
            uf_match = re.search(
                r"\b(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\b",
                linha,
                re.IGNORECASE,
            )
            uf = uf_match.group(1).lower() if uf_match else ""

            for nf in matches_nf:
              par = (nf, uf)
              if par not in itens_extraidos:
                itens_extraidos.append(par)
  except Exception as e:
    st.error(f"❌ Erro ao tentar ler o PDF: {e}")
  return itens_extraidos


def autenticar_drive():
  try:
    cred_data = {
        "token": None,
        "refresh_token": st.secrets["google_drive"]["refresh_token"],
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": st.secrets["google_drive"]["client_id"],
        "client_secret": st.secrets["google_drive"]["client_secret"],
        "scopes": SCOPES,
    }
    creds = Credentials.from_authorized_user_info(cred_data)
    return build("drive", "v3", credentials=creds)
  except Exception as e:
    st.error(f"❌ Erro ao autenticar com o Google Drive via Secrets: {e}")
    st.stop()


# --- DECLARAÇÃO DO UPLOADER PRIMEIRO ---
arquivos_upload = st.file_uploader(
    "📂 Envie um ou mais PDFs de Romaneio", type=["pdf"], accept_multiple_files=True
)

# --- VERIFICAÇÃO DEPOIS DO UPLOADER ---
if arquivos_upload:
  if st.button("🚀 Processar Romaneios Filtrando por UF"):
    try:
      servico = autenticar_drive()
    except Exception as e:
      st.error(f"Erro na autenticação: {e}")
      st.stop()

    for idx, arquivo_upload in enumerate(arquivos_upload):
      nome_romaneio_base = os.path.splitext(arquivo_upload.name)[0]

      st.markdown("---")
      st.subheader(f"📄 Romaneio: {arquivo_upload.name}")

      with st.spinner(f"Processando e filtrando {arquivo_upload.name}..."):
        bytes_pdf = arquivo_upload.read()
        dados_notas = extrair_dados_do_pdf(bytes_pdf)

        if not dados_notas:
          st.warning(
              f"⚠️ Nenhuma nota válida encontrada no romaneio:"
              f" {arquivo_upload.name}"
          )
          continue

        st.info(
            f"🎯 Encontradas {len(dados_notas)} combinações de notas e UFs neste"
            " romaneio."
        )

        notas_nao_encontradas = []
        total_encontrados_drive = 0

        # Criação do arquivo ZIP diretamente em memória RAM (Sem lixo no servidor)
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
          for numero, uf in dados_notas:
            if uf:
              query = (
                  f"mimeType='application/pdf' and name contains '{numero}' and"
                  f" name contains '{uf}' and trashed=false"
              )
            else:
              query = (
                  f"mimeType='application/pdf' and name contains '{numero}' and"
                  " trashed=false"
              )

            resultados = (
                servico.files()
                .list(q=query, spaces="drive", fields="files(id, name)")
                .execute()
            )
            arquivos = resultados.get("files", [])

            if not arquivos:
              notas_nao_encontradas.append(
                  f"{numero} (UF: {uf.upper() if uf else 'Não identificada'})"
              )
            else:
              for arquivo_alvo in arquivos:
                id_arquivo = arquivo_alvo["id"]
                nome_original = arquivo_alvo["name"]

                request_download = servico.files().get_media(fileId=id_arquivo)
                file_content = io.BytesIO()
                downloader = MediaIoBaseDownload(file_content, request_download)

                done = False
                while not done:
                  _, done = downloader.next_chunk()

                # Escreve direto no ZIP na memória
                zipf.writestr(nome_original, file_content.getvalue())
                total_encontrados_drive += 1

        zip_buffer.seek(0)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Itens", len(dados_notas))
        col2.metric("Notas Baixadas", total_encontrados_drive)
        col3.metric("Faltantes", len(notas_nao_encontradas))

        if notas_nao_encontradas:
          with st.expander(f"Ver itens faltando em {arquivo_upload.name}"):
            for nf in notas_nao_encontradas:
              st.write(f"- {nf}")

        if total_encontrados_drive > 0:
          zip_nome = f"notas_{nome_romaneio_base}_filtrado.zip"

          st.download_button(
              label=f"Baixar Pacote ZIP: {nome_romaneio_base}",
              data=zip_buffer,
              file_name=zip_nome,
              mime="application/zip",
              key=f"btn_zip_uf_{idx}",
          )
          st.success(
              f"✅ ZIP gerado com sucesso para: {arquivo_upload.name}"
          )
        else:
          st.warning(
              "⚠️ Nenhum arquivo correspondente com essa UF foi encontrado no"
              f" Drive para {arquivo_upload.name}."
          )
