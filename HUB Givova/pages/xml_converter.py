# 4. CNPJs (Captura todos e separa Emitente de Destinatário baseado na Chave)
    dados['cnpj_emitente'] = dados['chave'][6:20]
    dados['cnpj_destinatario'] = "00000000000000" # Fallback padrão
    
    cnpjs_encontrados = re.findall(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", texto_pdf)
    for c in cnpjs_encontrados:
        c_limpo = re.sub(r"\D", "", c)
        if c_limpo != dados['cnpj_emitente']:
            dados['cnpj_destinatario'] = c_limpo
            break

    # 5. VOLUMES E PESOS (NOVO)
    match_qvol = re.search(r"QUANTIDADE[\s\n]*(\d+)", texto_pdf, re.IGNORECASE)
    dados['qVol'] = match_qvol.group(1) if match_qvol else "1"

    match_esp = re.search(r"ESP[ÉE]CIE[\s\n]*([A-Za-z]+)", texto_pdf, re.IGNORECASE)
    dados['esp'] = match_esp.group(1).upper() if match_esp else "VOLUMES"

    match_pesoB = re.search(r"PESO BRUTO[\s\n]*([\d\.,]+)", texto_pdf, re.IGNORECASE)
    if match_pesoB:
        dados['pesoB'] = f"{float(match_pesoB.group(1).replace('.', '').replace(',', '.')):.3f}"
    else:
        dados['pesoB'] = "0.000"

    match_pesoL = re.search(r"PESO L[ÍI]QUIDO[\s\n]*([\d\.,]+)", texto_pdf, re.IGNORECASE)
    if match_pesoL:
        dados['pesoL'] = f"{float(match_pesoL.group(1).replace('.', '').replace(',', '.')):.3f}"
    else:
        dados['pesoL'] = "0.000"

    return dados
