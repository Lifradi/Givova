print("Qual o detalhamento de frete?")

linhas = []
while True:
    linha = input()
    linhas.append(linha)
    if "confirmar com um ok" in linha.lower():
        break

motorista = ""
cpf = ""
fone = ""
cavalo = ""
carretas = []
link = ""

for linha in linhas:
    linha = linha.strip()
    if linha.startswith("*MOT:"):
        motorista = linha.replace("*MOT:", "").strip()
    elif linha.startswith("*CPF:"):
        cpf = linha.replace("*CPF:", "").strip()
    elif linha.startswith("FONE:"):
        fone = linha.replace("FONE:", "").strip()
    elif linha.startswith("CAVALO:"):
        cavalo = linha.replace("CAVALO:", "").strip()
    elif linha.startswith("CARRETA:") and "R$" not in linha:
        carretas.append(linha.replace("CARRETA:", "").strip())
    elif "https://" in linha:
        link = "https://" + linha.split("https://")[1]
    elif linha.startswith("*VALOR DO FRETE:"):
        valor_frete = linha.replace("*VALOR DO FRETE:", "").strip()
    elif linha.startswith("*ADIANTAMENTO:"):
        adiantamento = linha.replace("*ADIANTAMENTO:", "").strip()
    elif linha.startswith("*SALDO:"):
        saldo = linha.replace("*SALDO:", "").strip()

print()
print("INFORMAÇÕES DO MOTORISTA")
print("Motorista:", motorista)
print("CPF:", cpf)
print("Telefone:", fone)
print("Cavalo:", cavalo)
for c in carretas:
    print("Carreta:", c)
print("Localizador:", link)
print("Valor do Frete:", valor_frete)
print("Adiantamento:", adiantamento)
print("Saldo:", saldo)
