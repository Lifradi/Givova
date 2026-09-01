import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Extrator de Boletos",
    page_icon="📑",
    layout="wide",
)

# --- VALIDAÇÃO DE SEGURANÇA DA SESSÃO ---
authentication_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")

if not authentication_status:
    st.error(
        "🔒 Acesso Negado! Por favor, faça o login na página principal do Hub"
        " primeiro."
    )
    if st.button("Ir para o Login"):
        st.switch_page("app.py")
    st.stop()

st.sidebar.markdown(f"👤 **Logado como:** {name}")

# --- INTERFACE PRINCIPAL ---
st.title("📑 Extrator de Dados de Boletos")
st.write(
    "Faça o upload dos PDFs de boletos bancários para extrair os dados e gerar "
    "a planilha de Controle de Pagamentos padronizada."
)

uploaded_files = st.file_uploader(
    "Envie os PDFs dos Boletos",
    type=["pdf"],
    accept_multiple_files=True,
    key="uploader_pdf_boletos",
)


def extrair_dados_boletos(arquivo_pdf):
    """Extrai os dados de boletos bancários lendo o arquivo PDF da memória."""
    boletos_extraidos = []

    try:
        with pdfplumber.open(arquivo_pdf) as pdf:
            # Consolida o texto de todas as páginas em uma única string caso um boleto divida páginas
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if not texto:
                    continue

                # Dicionário pré-preenchido com valores padrão/fixos conforme a regra da imagem
                dados = {
                    'tipo doc': 'outros',
                    'documento': '',
                    'fornecedor': '',
                    'total': '',
                    'emissão doc.': '',
                    'nº de parcelas': 1,
                    'vencimento': '',
                    'forma meio pgto': 'boleto',
                    'referencia/anotações': ''
                }

                # =========================================================
                # REGRAS DE EXTRAÇÃO PARA BOLETOS
                # =========================================================

                # 1. Vencimento
                # Tenta capturar do layout do boleto (ex: "Vencimento 22/09/2026")
                match_venc = re.search(r'(?:Vencimento|Data\s*de\s*Vencimento)\s*[:\s]*(\d{2}/\d{2}/\d{2,4})', texto, re.IGNORECASE)
                if match_venc:
                    dados['vencimento'] = match_venc.group(1).strip()

                # 2. Valor do Documento
                # Tenta capturar do layout do boleto (ex: "Valor documento 2.221,86")
                match_valor = re.search(r'(?:\(=\)\s*Valor\s*do\s*Documento|Valor\s*documento|Valor\s*Cobrado)\s*[:\s]*R?\$?\s*([\d.,]+)', texto, re.IGNORECASE)
                if match_valor:
                    dados['total'] = match_valor.group(1).strip()

                # 3. Data do Documento / Data de Emissão
                # Tenta capturar a data de emissão
                match_emissao = re.search(r'(?:Data\s*do\s*Doc(?:umento)?|Data\s*Emissã[o0])\s*[:\s]*(\d{2}/\d{2}/\d{2,4})', texto, re.IGNORECASE)
                if match_emissao:
                    dados['emissão doc.'] = match_emissao.group(1).strip()

                # 4. Número do Documento
                # Como observado nos layouts do Bradesco: "Nº documento 23978" 
                # Tenta extrair a chave específica ou recua pegando os números próximos ao cabeçalho.
                match_doc = re.search(r'N[ºo]?\s*documento[\s\S]*?(\d{4,10})', texto, re.IGNORECASE)
                if not match_doc:
                    # Alternativa se tiver no layout lateral: 09/00000062629-8 23978
                    match_doc = re.search(r'\d{2}/\d{11}-\w\s+(\d+)', texto)
                
                if match_doc:
                    dados['documento'] = match_doc.group(1).strip()

                # Só adiciona a linha se identificar pelo menos o documento ou valor ou vencimento
                if dados['vencimento'] or dados['total'] or dados['documento']:
                    boletos_extraidos.append(dados)

    except Exception as e:
        raise ValueError(f"Falha na leitura do PDF: {e}")

    return boletos_extraidos


# --- EXECUÇÃO DO PROCESSAMENTO ---
if uploaded_files:
    if st.button("🚀 Processar Boletos", type="primary"):
        barra = st.progress(0)
        total_arquivos = len(uploaded_files)
        todos_boletos = []
        erros = 0

        for i, arquivo in enumerate(uploaded_files):
            try:
                dados_arquivo = extrair_dados_boletos(arquivo)
                if dados_arquivo:
                    todos_boletos.extend(dados_arquivo)
            except Exception as e:
                st.error(f"❌ Erro ao processar {arquivo.name}: {e}")
                erros += 1

            # Atualiza barra de progresso
            barra.progress((i + 1) / total_arquivos)

        # Se encontrou algum boleto, gera a planilha
        if todos_boletos:
            if erros > 0:
                st.success(f"✨ Concluído com ressalvas! {len(todos_boletos)} registros de boletos extraídos. {erros} erros em arquivos.")
            else:
                st.success(f"✨ Sucesso absoluto! Foram extraídos {len(todos_boletos)} registros de boletos de {total_arquivos} PDFs.")

            df = pd.DataFrame(todos_boletos)

            # Ordem estrita das colunas conforme tabela de requisitos da imagem
            colunas_ordem = [
                'tipo doc',
                'documento',
                'fornecedor',
                'total',
                'emissão doc.',
                'nº de parcelas',
                'vencimento',
                'forma meio pgto',
                'referencia/anotações'
            ]

            # Preenche colunas ausentes para evitar erros
            for col in colunas_ordem:
                if col not in df.columns:
                    df[col] = ''

            df = df[colunas_ordem]

            # Gerar arquivo Excel em memória
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Boletos Extraídos')

            # Botão para Download
            st.download_button(
                label="📥 Baixar Planilha de Boletos (.XLSX)",
                data=excel_buffer.getvalue(),
                file_name=f"controle_boletos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            st.warning("⚠️ Nenhum boleto foi identificado. Verifique se os PDFs contêm o texto legível esperado.")
