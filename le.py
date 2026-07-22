import os
import re
import csv
import unicodedata
from PIL import Image
from pdf2image import convert_from_path
import pytesseract

# ==============================
# CONFIG
# ==============================
#PASTA_IMAGENS = "/home/node/imagens"
#CSV_PESSOAS   = "/home/node/data/pessoas.csv"
PASTA_IMAGENS = "data/"
CSV_PESSOAS   = "pessoas.csv"

# ==============================
# REGEX
# ==============================
# Valor: R$ 65,31 ou 65,31 ou R$ 1.234,56 - mais flexível
PADRAO_VALOR = r"(?:R\$\s*)?\d{1,3}(?:[.,]\d{3})*[.,]\d{2}\b"
# Data em múltiplos formatos: aceita abreviações (JAN, FEV) ou nomes completos (JANEIRO, FEVEREIRO)
# Espaços opcionais: 08FEV2026 ou 08 FEV 2026 ou 08FEV 2026 etc
PADRAO_DATA  = r"\b\d{1,2}\s*(?:JANEIRO|FEVEREIRO|MARCO|MARÇO|ABRIL|MAIO|JUNHO|JULHO|AGOSTO|SETEMBRO|OUTUBRO|NOVEMBRO|DEZEMBRO|JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ)\s*\d{4}\b|\b\d{2}/\d{2}/\d{4}\b|\b\d{2}/\d{2}/\d{2}\b|\b\d{2}-\d{2}-\d{4}\b"

# HH:MI:SS ou HH:MI (com ou sem separadores)
PADRAO_HORA  = r"\b([01]\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?\b"

# ==============================
# UTIL
# ==============================
def normalizar(txt):
    if not txt:
        return ""
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return txt.upper().strip()

# ==============================
# CSV
# ==============================
def carregar_pessoas():
    pessoas = []

    with open(CSV_PESSOAS, encoding="utf-8-sig", newline="") as f:
        amostra = f.read(2048)
        f.seek(0)

        if ";" in amostra:
            delim = ";"
        elif "\t" in amostra:
            delim = "\t"
        else:
            delim = ","

        reader = csv.reader(f, delimiter=delim)
        cabecalho = next(reader)
        cab = [normalizar(c) for c in cabecalho]

        POSSIVEIS_ID   = ["ID", "CODIGO", "COD", "IDENTIFICADOR"]
        POSSIVEIS_NOME = ["NOME COMPLETO", "NOME", "PESSOA"]

        idx_id = next((cab.index(c) for c in POSSIVEIS_ID if c in cab), None)
        idx_nm = next((cab.index(c) for c in POSSIVEIS_NOME if c in cab), None)

        if idx_id is None or idx_nm is None:
            raise Exception("CSV INVALIDO")

        for row in reader:
            if len(row) <= max(idx_id, idx_nm):
                continue

            pessoas.append({
                "id": re.sub(r"\s+", "", row[idx_id]),
                "nome": normalizar(row[idx_nm])
            })

    return pessoas

def achar_id(nome, pessoas):
    nome = normalizar(nome)

    # Tentativa 1: correspondência exata
    for p in pessoas:
        if p["nome"] == nome:
            return p["id"]

    # Tentativa 2: correspondência por tokens (todas as palavras do nome extraído
    # estão presentes no nome cadastrado) — útil para variações/ordem/abreviações
    tokens = [t for t in nome.split() if len(t) > 1]
    if tokens:
        for p in pessoas:
            if all(tok in p["nome"] for tok in tokens):
                return p["id"]

    return None

# ==============================
# OCR
# ==============================
MESES_ABREV = {
    "JAN": "01", "FEV": "02", "MAR": "03", "ABR": "04",
    "MAI": "05", "JUN": "06", "JUL": "07", "AGO": "08",
    "SET": "09", "OUT": "10", "NOV": "11", "DEZ": "12",
    # Nomes completos
    "JANEIRO": "01", "FEVEREIRO": "02", "MARCO": "03", "MARÇO": "03",
    "ABRIL": "04", "MAIO": "05", "JUNHO": "06", "JULHO": "07",
    "AGOSTO": "08", "SETEMBRO": "09", "OUTUBRO": "10",
    "NOVEMBRO": "11", "DEZEMBRO": "12"
}

def converter_data_textual(data_texto):
    """
    Converte data em formato textual (DD MÊS AAAA) para DD/MM/YY
    Aceita variações: 05 FEV 2026, 5 FEV 2026, 05FEV2026, 05 fevereiro 2026, etc
    Espaços opcionais entre dia/mês/ano
    Exemplo: 05 FEV 2026 -> 05/02/26 ou 05FEV2026 -> 05/02/26
    """
    if not data_texto:
        return None
    
    # Tenta extrair DD MÊS AAAA com espaços opcionais (abreviação ou nome completo)
    match = re.search(r"\b(\d{1,2})\s*([A-Z\u00C0-\u00FC]+)\s*(\d{4})\b", data_texto, re.IGNORECASE)
    if match:
        dia, mes_texto, ano = match.groups()
        
        # Normaliza o mês: remove acentos
        mes_texto_norm = normalizar(mes_texto)
        
        # Garante que dia tem 2 dígitos
        dia = dia.zfill(2)
        
        if mes_texto_norm in MESES_ABREV:
            mes = MESES_ABREV[mes_texto_norm]
            ano_2dig = ano[-2:]  # Pega últimos 2 dígitos do ano
            return f"{dia}/{mes}/{ano_2dig}"
    
    return None

def ocr_imagem(imagem):
    texto = pytesseract.image_to_string(
        imagem,
        lang="por",
        config="--psm 6"
    )
    return [l.strip() for l in texto.splitlines() if l.strip()]

def extrair_nome_do_texto(linhas):
    """
    Extrai o nome do comprovante (do OCR).
    Procura por "Nome:" ou "Nome" seguido de qualquer conteúdo
    Retorna o nome encontrado ou None se não conseguir extrair.
    """
    texto = "\n".join(linhas)

    # Procura por "Nome" seguido de qualquer coisa até fim de linha
    # Isso captura: "Nome Aline Kelly", "Nome: Aline Kelly", "Nome                 Aline Kelly", etc
    match = re.search(r"(?:Nome|NOME)\s*:?\s*(.+?)(?:\n|$)", texto, re.IGNORECASE)
    if match:
        nome_raw = match.group(1).strip()
        # Normaliza primeiro (remove acentos, maiúsculas, trim) e depois remove
        # caracteres não alfabéticos remanescentes.
        nome_norm = normalizar(nome_raw)
        nome = re.sub(r"[^A-Z\s]", "", nome_norm)

        if len(nome.split()) >= 2:  # Pelo menos 2 palavras
            return nome
    
    # Se não encontrou com "Nome", tenta outros labels
    padroes_secundarios = [
        r"(?:Para|PARA|Titular|TITULAR|Beneficiario|BENEFICIARIO)\s*:?\s*(.+?)(?:\n|$)",
    ]
    
    for padrao in padroes_secundarios:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            nome_raw = match.group(1).strip()
            nome_norm = normalizar(nome_raw)
            nome = re.sub(r"[^A-Z\s]", "", nome_norm)

            if len(nome.split()) >= 2:
                return nome
    
    return None

def extrair_hora(texto):
    """
    Extrai hora em vários formatos: HH:MI:SS, HH-MI-SS, HH:MI, HH-MI, HHMI, 14h21, 14h21m55, etc
    Garante validação de horas (00-23), minutos (00-59), segundos (00-59)
    Corrige OCR comum: 14 32 55 -> 14:32:55 ou 14 32 -> 14:32 ou 1432 -> 14:32 ou 14h21 -> 14:21
    """
    # Primeiro, normaliza hífens para dois-pontos
    texto_norm = texto.replace("-", ":")
    
    # Corrige OCR: espaços ou pontos entre digitos
    texto_corrigido = re.sub(
        r"\b([01]\d|2[0-3])[\s\.]([0-5]\d)[\s\.]([0-5]\d)\b",
        r"\1:\2:\3",
        texto_norm
    )
    texto_corrigido = re.sub(
        r"\b([01]\d|2[0-3])[\s\.]([0-5]\d)\b(?![\s\.:])",
        r"\1:\2",
        texto_corrigido
    )

    # Busca formato HH:MM:SS (inclui hífens convertidos)
    match_hms = re.search(r"\b([01]\d|2[0-3]):([0-5]\d):([0-5]\d)\b", texto_corrigido)
    if match_hms:
        h, m, s = match_hms.groups()
        return f"{h}:{m}:{s}"

    # Procura por formato com 'h' e 'm': 14h21m55 ou 14h21
    match_hm = re.search(r"\b([01]\d|2[0-3])h([0-5]\d)(?:m([0-5]\d))?\b", texto_corrigido)
    if match_hm:
        h, m, s = match_hm.groups()
        if s:
            return f"{h}:{m}:{s}"
        else:
            return f"{h}:{m}"

    # Busca HH:MM (com dois-pontos ou hífen)
    match_hm_sep = re.search(r"\b([01]\d|2[0-3]):([0-5]\d)\b", texto_corrigido)
    if match_hm_sep:
        h, m = match_hm_sep.groups()
        return f"{h}:{m}"

    # Procura por formato HHMI (sem separadores) - 4 dígitos válidos
    match_sem_sep = re.search(r"\b([01]\d|2[0-3])([0-5]\d)\b", texto_corrigido)
    if match_sem_sep:
        h, m = match_sem_sep.groups()
        return f"{h}:{m}"

    return None

def extrair_valor_correto(texto):
    """
    Extrai o valor mais apropriado do texto.
    Busca por padrões que indicam um valor principal (após 'Valor:', 'Total:', etc)
    Remove a label "Valor" do resultado
    """
    if not texto:
        return None

    # Normaliza espaços e caracteres comuns que o OCR costuma introduzir
    txt = texto.replace("\xa0", " ")
    txt = txt.replace("\n", " ")
    txt = re.sub(r"\s+", " ", txt)

    # Normaliza espaços dentro de números:
    # - Se houver espaço antes de 2 dígitos finais, trata como separador decimal (65 31 -> 65,31)
    # - Espaços antes de grupos de 3 dígitos viram separador de milhar (1 234 -> 1.234)
    # - Remove espaços restantes entre dígitos
    txt = re.sub(r"(?<=\d)\s+(?=\d{2}\b)", ",", txt)
    txt = re.sub(r"(?<=\d)\s+(?=\d{3}\b)", ".", txt)
    txt = re.sub(r"(?<=\d)\s+(?=\d)", "", txt)

    # Normaliza variações de R$ (ex: "R $", "R$", "R S") para "R$ "
    txt = re.sub(r"R\s*\$|R\s+S", "R$", txt, flags=re.IGNORECASE)

    # Tenta encontrar valor após label "Valor" (com ou sem ':')
    # Aceita qualquer quantidade de dígitos antes do separador decimal
    match = re.search(r"(?:Valor)\s*:??\s*(R\$\s*)?(\d+[.,]\d{2})", txt, re.IGNORECASE)
    if match:
        valor_encontrado = match.group(2)
        if match.group(1):
            valor_encontrado = "R$ " + valor_encontrado
        return valor_encontrado

    # Se não encontrou pela label, tenta capturar qualquer padrão de valor no texto normalizado
    valores = re.findall(PADRAO_VALOR, txt)
    if valores:
        return valores[0]

    # Fallback: captura números simples com casas decimais (ex: 1234,56 ou 65.31)
    valores_simples = re.findall(r"\d+[.,]\d{2}", txt)
    if valores_simples:
        return valores_simples[0]

    return None

# ==============================
# PROCESSAMENTO
# ==============================
def processar_arquivo(arquivo, pessoas):
    caminho = os.path.join(PASTA_IMAGENS, arquivo)

    try:
        linhas = []

        if arquivo.lower().endswith(".pdf"):
            paginas = convert_from_path(caminho, dpi=300)
            for p in paginas:
                linhas.extend(ocr_imagem(p))
        else:
            img = Image.open(caminho)
            linhas = ocr_imagem(img)

        texto = "\n".join(linhas)

        # Extrai valores usando a função melhorada
        valor = extrair_valor_correto(texto)
        
        # Extrai datas (agora suporta DD MÊS AAAA)
        datas = re.findall(PADRAO_DATA, texto, re.IGNORECASE)
        
        # Converte data textual para DD/MM/YY se necessário
        data_final = None
        if datas:
            for d in datas:
                # Se for data textual (DD MÊS AAAA), converte para DD/MM/YY
                if re.search(r"\d{2}\s+[A-Z]{3}\s+\d{4}", d, re.IGNORECASE):
                    data_final = converter_data_textual(d)
                    if data_final:
                        break
                # Se for DD/MM/AAAA, converte para DD/MM/YY
                elif re.match(r"\d{2}/\d{2}/\d{4}", d):
                    data_final = d[:5] + d[-2:]  # Pega DD/MM/YY
                    break
                # Se já for DD/MM/YY, usa como está
                elif re.match(r"\d{2}/\d{2}/\d{2}", d):
                    data_final = d
                    break
        
        # Extrai hora
        hora = extrair_hora(texto)

        # Extrai nome DO COMPROVANTE
        nome = extrair_nome_do_texto(linhas)
        
        # Busca o ID no CSV usando o nome extraído
        pid = achar_id(nome, pessoas) if nome else None

        # Debug: mostrar todos os valores encontrados
        todos_valores = re.findall(PADRAO_VALOR, texto)
        
        print(f"*ID:* {pid or 'NAO ENCONTRADO'}")
        print(f"*NOME:* {nome or 'NAO ENCONTRADO'}")
        print(f"*VALOR:* {valor or 'NAO ENCONTRADO'}")
        if len(todos_valores) > 1:
            print(f"  [DEBUG] Todos os valores encontrados: {todos_valores}")
        print(f"*DATA:* {data_final or 'NAO ENCONTRADA'}")
        print(f"*HORA:* {hora or 'NAO ENCONTRADA'}")
        print()

        # Temporariamente não removemos as imagens para debug/localização de problemas
        # os.remove(caminho)

    except Exception as e:
        print(f"ERRO AO PROCESSAR {arquivo}: {e}")

# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    pessoas = carregar_pessoas()

    arquivos = [
        f for f in os.listdir(PASTA_IMAGENS)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".pdf"))
    ]

    for arq in arquivos:
        processar_arquivo(arq, pessoas)