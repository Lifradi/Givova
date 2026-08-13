import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Extrator de Faturas",
    page_icon="📄",
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
st.title("📄 Extrator de Dados de Faturas")
st.write(
    "Faça o upload dos PDFs de faturas para extrair os dados e gerar a "
    "planilha de Controle de Operação padronizada."
)

uploaded_files = st.file_uploader(
    "Envie os PDFs das Faturas",
    type=["pdf"],
    accept_multiple_files=True,
    key="uploader_pdf_faturas",
)

def extrair_dados_faturas(arquivo_pdf):
    """Extrai os dados da fatura lendo o arquivo diretamente da memória."""
    faturas_extraidas = []
    
    try:
        # pdfplumber consegue ler diretamente o objeto de arquivo do Streamlit
        with pdfplumber.open(arquivo_pdf) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if not texto:
                    continue
                
                # Dicionário com as colunas iniciais vazias
                dados = {
                    'OS': '',
                    'cidade': '',
                    'VENC': '',
                    'VALOR': '',
                    'FACTORING': '', 
                    'DATA OPERAÇÃO': '',
                    'numero fatura': '',
                    'empresa': ''
                }
                
                # =========================================================
                # REGRAS DE EXTRAÇÃO FLEXÍVEIS E INDEPENDENTES
                # =========================================================
                
                # 1. Número da Fatura (Procura isoladamente)
                match_fat = re.search(r'FATURA\s+(\d+)', texto)
                if match_fat:
                    dados['numero fatura'] = f"fat {match_fat.group(1)}"

                # 2. Vencimento e Valor 
                match_cobranca = re.search(r'(\d{4,6})[\s|]+(\d{2}/\d{2}/\d{4})[\s|]+(?:0,00[\s|]+)?([\d.,]+)', texto)
                if match_cobranca:
                    dados['VENC'] = match_cobranca.group(2)
                    dados['VALOR'] = f"R$ {match_cobranca.group(3)}"
                    if not dados['numero fatura']:
                        dados['numero fatura'] = f"fat {match_cobranca.group(1)}"

                # 3. Cidade (Formato CIDADE-UF)
                match_cidade = re.search(r'([A-Za-z\s]+-[A-Za-z]{2})[\s\n]', texto)
                if match_cidade:
                    dados['cidade'] = match_cidade.group(1).split('-')[0].strip().lower()

                # 4. OS (Número do Conhecimento)
                match_os = re.search(r'(\d{4,6})\s+1\s+\d{2}/\d{2}/\d{2,4}', texto)
                if match_os:
                    dados['OS'] = f"cte usado {match_os.group(1)}"

                # 5. Data da Operação (Data da NF-e)
                match_data_op = re.search(r'NF-e\s+\d+[\s\n]+(\d{2}/\d{2}/\d{4})', texto)
                if match_data_op:
                    dados['DATA OPERAÇÃO'] = match_data_op.group(1)

                # 6. Empresa
                if "GIVOVA TRANSPORTES" in texto.upper():
                    dados['empresa'] = "giv ocam"

                # Se achou um número de fatura na página, salva a linha na lista
                if dados['numero fatura']:
                    faturas_extraidas.append(dados)

    except Exception as e:
        raise ValueError(f"Falha na leitura do PDF: {e}")
        
    return faturas_extraidas

# --- EXECUÇÃO DO PROCESSAMENTO ---
if uploaded_files:
    if st.button("🚀 Processar Faturas", type="primary"):
        barra = st.progress(0)
        total_arquivos = len(uploaded_files)
        todas_faturas = []
        erros = 0

        for i, arquivo in enumerate(uploaded_files):
            try:
                dados_arquivo = extrair_dados_faturas(arquivo)
                if dados_arquivo:
                    todas_faturas.extend(dados_arquivo)
            except Exception as e:
                st.error(f"❌ Erro ao processar {arquivo.name}: {e}")
                erros += 1
            
            # Atualiza barra de progresso
            barra.progress((i + 1) / total_arquivos)

        # Se encontrou alguma fatura, gera a planilha
        if todas_faturas:
            if erros > 0:
                st.success(f"✨ Concluído com ressalvas! {len(todas_faturas)} faturas extraídas. {erros} erros em arquivos.")
            else:
                st.success(f"✨ Sucesso absoluto! Foram extraídas {len(todas_faturas)} faturas de {total_arquivos} PDFs.")

            df = pd.DataFrame(todas_faturas)
            
            # Garante a ordem correta das colunas
            colunas_ordem = ['OS', 'cidade', 'VENC', 'VALOR', 'FACTORING', 'DATA OPERAÇÃO', 'numero fatura', 'empresa']
            
            # Preenche colunas ausentes caso nenhuma fatura tenha achado aquele campo específico
            for col in colunas_ordem:
                if col not in df.columns:
                    df[col] = ''
            
            df = df[colunas_ordem]
            
            # Gerar arquivo Excel em memória
            excel_buffer = io.BytesIO()
            # Precisamos do 'openpyxl' ou 'xlsxwriter' instalado para exportar Excel
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Faturas Extraídas')

            # Botão para Download
            st.download_button(
                label="📥 Baixar Planilha Preenchida (.XLSX)",
                data=excel_buffer.getvalue(),
                file_name=f"controle_operacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            st.warning("⚠️ Nenhuma fatura foi extraída. Verifique se os PDFs estão legíveis ou no layout correto.")
