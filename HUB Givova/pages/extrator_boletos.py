import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
from datetime import datetime

# --- config da pagina ---
st.set_page_config(
    page_title="Extrator de Boletos",
    layout="wide",
)

# --- Check de login ---
authentication_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")

if not authentication_status:
    st.error(
        "Acesso Negado! Por favor, faca o login na pagina principal do Hub"
        " primeiro."
    )
    if st.button("Ir para o Login"):
        st.switch_page("app.py")
    st.stop()

st.sidebar.markdown(f"Logado como: {name}")

# --- main UI ---
st.title("Extrator de Dados de Boletos")
st.write(
    "Upload dos PDFs de boletos bancarios para extrair os dados e gerar "
    "a planilha de Controle de Pagamentos."
)

uploaded_files = st.file_uploader(
    "Envie os PDFs",
    type=["pdf"],
    accept_multiple_files=True,
    key="uploader_pdf_boletos",
)


def process_boleto_data(arquivo_pdf):
    # Funcao que extrai os dados lendo o arquivo PDF da memoria
    parsed_docs = []

    try:
        with pdfplumber.open(arquivo_pdf) as pdf:
            # junta as pags numa string so
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if not texto:
                    continue

                # default dict values
                row_data = {
                    'tipo doc': 'outros',
                    'documento': '',
                    'fornecedor': '',  # deixar vazio pra preencher o codigo no sistema dps
                    'total': '',
                    'emissão doc.': '',
                    'nº de parcelas': 1,
                    'vencimento': '',
                    'forma meio pgto': 'boleto',
                    'referencia/anotações': ''
                }

                # =========================================================
                # REGEX RULES
                # =========================================================

                # Vencimento
                # \D*? pula qualque caracter nao numerico ate achar a data
                match_date = re.search(r'Vencimento\D*?(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE)
                if match_date:
                    row_data['vencimento'] = match_date.group(1).strip()

                # Valor do Documento (Total)
                # Formato br de moeda pra nao pegar sujeira tipo numero da carteira
                match_amount = re.search(r'Valor\s*documento\D*?(\d{1,3}(?:\.\d{3})*,\d{2})', texto, re.IGNORECASE)
                if match_amount:
                    row_data['total'] = match_amount.group(1).strip()

                # Data de Emissão
                match_emissao = re.search(r'Data\s*do\s*documento\D*?(\d{2}/\d{2}/\d{4})', texto, re.IGNORECASE)
                if match_emissao:
                    row_data['emissão doc.'] = match_emissao.group(1).strip()

                # Número do Documento
                # pega os digitos logo apos o nosso numero no bradesco
                match_doc = re.search(r'09/\d{11}-[0-9A-Za-z]\s+(\d{4,8})', texto)
                if not match_doc:
                    # fallback
                    match_doc = re.search(r'Número\s*do\s*documento\D*?(\d{4,8})\b', texto, re.IGNORECASE)
                
                if match_doc:
                    row_data['documento'] = match_doc.group(1).strip()

                # Adiciona o dict se achou pelo menos 1 item util
                if row_data['vencimento'] or row_data['total'] or row_data['documento']:
                    parsed_docs.append(row_data)

    except Exception as e:
        # trata excessao de leitura
        raise ValueError(f"Erro na leitura do pdf: {e}")

    return parsed_docs


# --- ACTION ---
if uploaded_files:
    if st.button("Processar Boletos", type="primary"):
        barra = st.progress(0)
        total_arquivos = len(uploaded_files)
        all_records = []
        errors_count = 0

        for i, arquivo in enumerate(uploaded_files):
            try:
                dados_arquivo = process_boleto_data(arquivo)
                if dados_arquivo:
                    all_records.extend(dados_arquivo)
            except Exception as e:
                st.error(f"Erro ao processar {arquivo.name}: {e}")
                errors_count += 1

            # update progress
            barra.progress((i + 1) / total_arquivos)

        # Build dataframe se tem dados
        if all_records:
            if errors_count > 0:
                st.success(f"Finalizado. {len(all_records)} boletos extraidos com {errors_count} erros.")
            else:
                st.success(f"Sucesso. {len(all_records)} registros extraidos de {total_arquivos} arquivos.")

            df = pd.DataFrame(all_records)

            # Ordem correta do layout
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

            # garante todas as colunas
            for col in colunas_ordem:
                if col not in df.columns:
                    df[col] = ''

            df = df[colunas_ordem]

            # Export to Excel
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Boletos')

            st.download_button(
                label="Baixar Planilha (.xlsx)",
                data=excel_buffer.getvalue(),
                file_name=f"boletos_extract_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            st.warning("Nenhum dado encontrado nos arquivos.")
