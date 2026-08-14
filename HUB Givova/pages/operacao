from datetime import datetime
import io
import re
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
import streamlit as st
import streamlit_authenticator as stauth

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Operação FIDIC",
    page_icon="📊",
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

st.title("📊 Oeração FIDIC")
st.write(
    "Envie a **Planilha 1** (com múltiplas abas) e a **Planilha 2** de referência. "
    "O sistema cruzará os números de CT-es (removendo sufixos como `-CTE` e tratando "
    "divergências entre texto e número) e destacará em verde as linhas correspondentes."
)

col1, col2 = st.columns(2)
with col1:
    uploaded_p1 = st.file_uploader(
        "Envie a Planilha 1 (.xlsx)", type=["xlsx"], key="p1"
    )
with col2:
    uploaded_p2 = st.file_uploader(
        "Envie a Planilha 2 de Referência (.xls ou .xlsx)",
        type=["xls", "xlsx"],
        key="p2",
    )


def limpar_cte(valor):
    """Padroniza o valor do CTe removendo sufixos e formatações indesejadas."""
    if pd.isna(valor):
        return ""
    val_str = str(valor).strip()
    val_str = re.sub(r"[-_\s]*cte\b", "", val_str, flags=re.IGNORECASE)
    if val_str.endswith(".0"):
        val_str = val_str[:-2]
    return val_str.strip()


if uploaded_p1 and uploaded_p2:
    if st.button("🚀 Processar e Destacar Planilha", type="primary"):
        with st.spinner("Processando e cruzando os dados..."):
            try:
                bytes_p1 = uploaded_p1.read()
                bytes_p2 = uploaded_p2.read()

                # 1. Lê a Planilha 2 para extrair o conjunto de referência
                xls2 = pd.ExcelFile(io.BytesIO(bytes_p2))
                ctes_referencia = set()
                for sheet in xls2.sheet_names:
                    df_p2 = pd.read_excel(
                        io.BytesIO(bytes_p2), sheet_name=sheet
                    )
                    for col in df_p2.columns:
                        limpos = df_p2[col].apply(limpar_cte)
                        for val in limpos:
                            if val:
                                ctes_referencia.add(val)

                # 2. Carrega a Planilha 1 mantendo a formatação original via openpyxl
                wb = load_workbook(io.BytesIO(bytes_p1))
                fill_verde = PatternFill(
                    start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"
                )

                total_destaques = 0

                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    df_p1_sheet = pd.read_excel(
                        io.BytesIO(bytes_p1), sheet_name=sheet_name
                    )

                    if df_p1_sheet.empty:
                        continue

                    # Identifica automaticamente a coluna de CTes na aba
                    coluna_cte = None
                    max_matches = 0
                    for col in df_p1_sheet.columns:
                        matches = (
                            df_p1_sheet[col]
                            .apply(limpar_cte)
                            .isin(ctes_referencia)
                            .sum()
                        )
                        if matches > max_matches:
                            max_matches = matches
                            coluna_cte = col

                    if coluna_cte and max_matches > 0:
                        col_idx = (
                            list(df_p1_sheet.columns).index(coluna_cte) + 1
                        )
                        for row_idx in range(2, ws.max_row + 1):
                            cell_value = ws.cell(
                                row=row_idx, column=col_idx
                            ).value
                            if cell_value is not None:
                                val_limpo = limpar_cte(cell_value)
                                if val_limpo in ctes_referencia:
                                    total_destaques += 1
                                    for col_i in range(1, ws.max_column + 1):
                                        ws.cell(
                                            row=row_idx, column=col_i
                                        ).fill = fill_verde

                # Salva o arquivo resultante em memória
                output = io.BytesIO()
                wb.save(output)
                processed_data = output.getvalue()

                st.success(
                    f"✨ Processamento concluído com sucesso! Foram"
                    f" destacados {total_destaques} registros encontrados."
                )

                st.download_button(
                    label="📥 Baixar Planilha Destacada (.XLSX)",
                    data=processed_data,
                    file_name=(
                        "planilha_destacada_"
                        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    ),
                    mime=(
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    ),
                    use_container_width=True,
                )

            except Exception as e:
                st.error(f"❌ Erro crítico ao processar as planilhas: {e}")
else:
    st.info(
        "💡 Por favor, envie ambas as planilhas acima para habilitar o"
        " processamento."
    )
