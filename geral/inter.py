import os
import re
import unicodedata
import sys
import json

try:    
    from PIL import Image
    import pytesseract
except Exception:
    pytesseract = None

if sys.platform == "win32":
    PASTA_IMAGENS = r"C:\Users\brunoquaiatti\Documents\GitHub\gazofilacio-scripts\geral"
    JSON_PESSOAS  = r"C:\Users\brunoquaiatti\Documents\GitHub\gazofilacio-scripts\geral\pessoas.json"
else:
    PASTA_IMAGENS = "/home/node/data/"
    JSON_PESSOAS  = "/home/node/data/pessoas.json"


# PADROES
PADRAO_VALOR = r"(?:R\$\s*)?\d{1,3}(?:[.,]\d{3})*[.,]\d{2}\b"
PADRAO_DATA  = r"\b\d{1,2}\s*(?:JANEIRO|FEVEREIRO|MARCO|MARÇO|ABRIL|MAIO|JUNHO|JULHO|AGOSTO|SETEMBRO|OUTUBRO|NOVEMBRO|DEZEMBRO|JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ)\s*\d{4}\b|\b\d{2}/\d{2}/\d{4}\b|\b\d{2}/\d{2}/\d{2}\b|\b\d{2}-\d{2}-\d{4}\b"
PADRAO_DATA_COM_DIA_SEMANA = r"(?:SEGUNDA|TERCA|TERÇA|QUARTA|QUINTA|SEXTA|SABADO|SÁBADO|DOMINGO)\s*,?\s*(\d{2}/\d{2}/\d{2,4})"
PADRAO_HORA  = r"\b([01]\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?\b"

def normalizar(txt):
    if not txt:
        return ""
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return txt.upper().strip()

def title_case(txt):
    """Converte texto para Title Case (Aaaa Bbbbb Ccccc)"""
    if not txt:
        return txt
    return " ".join(word.capitalize() for word in txt.split())

def carregar_pessoas_json():
    """Carrega pessoas a partir de um arquivo JSON local.
    Retorna lista de dicts {'id': <str>, 'nome': <NORMALIZED_NAME>}.
    """
    pessoas = []
    try:
        with open(JSON_PESSOAS, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    items = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        if "data" in data and isinstance(data["data"], list):
            items = data["data"]
        else:
            # procura a primeira lista dentro do dict
            for v in data.values():
                if isinstance(v, list):
                    items = v
                    break
            if not items:
                # trata um único objeto como lista de 1
                items = [data]
    else:
        return []

    for it in items:
        if not isinstance(it, dict):
            continue
        id_keys = [k for k in ("codigo_dizimista", "codigo", "codigo_id", "id", "ID") if k in it]
        name_keys = [k for k in ("nome_completo", "nome", "full_name", "name", "NOME") if k in it]

        if not name_keys or not id_keys:
            for k, v in it.items():
                if not name_keys and isinstance(v, str) and re.search(r"[A-Za-zÀ-ú]", v) and len(v.split()) >= 2:
                    name_keys = [k]
                if not id_keys and (isinstance(v, (str, int)) and re.fullmatch(r"\d+", str(v))):
                    id_keys = [k]

        if name_keys and id_keys:
            idv = str(it[id_keys[0]])
            namev = it[name_keys[0]]
            pessoas.append({"id": re.sub(r"\s+", "", idv), "nome": normalizar(str(namev))})

    return pessoas

def achar_id(nome, pessoas):
    """
    Retorna o ID da pessoa usando SOMENTE correspondência exata
    após normalização (sem fallbacks por tokens).
    """
    nome_norm = normalizar(nome)
    for p in pessoas:
        if p["nome"] == nome_norm:
            return p["id"]
    return None

MESES_ABREV = {
    # Português curto
    "JAN": "01", "FEV": "02", "MAR": "03", "ABR": "04",
    "MAI": "05", "JUN": "06", "JUL": "07", "AGO": "08",
    "SET": "09", "OUT": "10", "NOV": "11", "DEZ": "12",
    # Português completo
    "JANEIRO": "01", "FEVEREIRO": "02", "MARCO": "03", "MARÇO": "03",
    "ABRIL": "04", "MAIO": "05", "JUNHO": "06", "JULHO": "07",
    "AGOSTO": "08", "SETEMBRO": "09", "OUTUBRO": "10",
    "NOVEMBRO": "11", "DEZEMBRO": "12"
}

def converter_data_textual(data_texto):
    if not data_texto:
        return None
    # Tratamento de espaços não-quebreáveis e múltiplos espaços
    data_texto = data_texto.replace("\xa0", " ")
    data_texto = re.sub(r"\s+", " ", data_texto).strip()
    
    # Padrão mais flexível: DD MES AAAA, com ou sem espaços extras
    match = re.search(r"\b(\d{1,2})\s+([A-Z\u00C0-\u00FC]+)\s+(\d{4})\b", data_texto, re.IGNORECASE)
    if match:
        dia, mes_texto, ano = match.groups()
        mes_texto_norm = normalizar(mes_texto)
        dia = dia.zfill(2)
        if mes_texto_norm in MESES_ABREV:
            mes = MESES_ABREV[mes_texto_norm]
            ano_2dig = ano[-2:]
            return f"{dia}/{mes}/{ano_2dig}"
    return None

def extrair_hora(texto):
    texto_norm = texto.replace("-", ":")
    texto_corrigido = re.sub(r"\b([01]\d|2[0-3])[\s\.]([0-5]\d)[\s\.]([0-5]\d)\b", r"\1:\2:\3", texto_norm)
    texto_corrigido = re.sub(r"\b([01]\d|2[0-3])[\s\.]([0-5]\d)\b(?![\s\.:])", r"\1:\2", texto_corrigido)
    match_hms = re.search(r"\b([01]\d|2[0-3]):([0-5]\d):([0-5]\d)\b", texto_corrigido)
    if match_hms:
        h, m, s = match_hms.groups()
        return f"{h}:{m}:{s}"
    match_hm = re.search(r"\b([01]\d|2[0-3])h([0-5]\d)(?:m([0-5]\d))?\b", texto_corrigido)
    if match_hm:
        h, m, s = match_hm.groups()
        if s:
            return f"{h}:{m}:{s}"
        else:
            return f"{h}:{m}"
    match_hm_sep = re.search(r"\b([01]\d|2[0-3]):([0-5]\d)\b", texto_corrigido)
    if match_hm_sep:
        h, m = match_hm_sep.groups()
        return f"{h}:{m}"
    match_sem_sep = re.search(r"\b([01]\d|2[0-3])([0-5]\d)\b", texto_corrigido)
    if match_sem_sep:
        h, m = match_sem_sep.groups()
        return f"{h}:{m}"
    return None

def extrair_nome_do_texto(linhas):
    texto = "\n".join(linhas)

    # 1) Origem tem prioridade absoluta: tenta mesma linha primeiro
    m = re.search(r"(?:Origem)\s*:??\s*(.+?)(?:\n|$)", texto, re.IGNORECASE)
    if m:
        nome_raw = m.group(1).strip()
        if re.search(r"[A-Za-zÀ-ú]", nome_raw):
            nome_norm = normalizar(nome_raw)
            nome = re.sub(r"[^A-Z\s]", "", nome_norm)
            if len(nome.split()) >= 2:
                return nome

    # 2) Se 'Origem' aparece em linha isolada, pega próxima linha não vazia como nome
    for i, ln in enumerate(linhas):
        if "ORIGEM" in normalizar(ln):
            # tenta conteúdo na mesma linha após 'Origem'
            m2 = re.search(r"Origem\s*:??\s*(.+)$", ln, re.IGNORECASE)
            if m2 and re.search(r"[A-Za-zÀ-ú]", m2.group(1)):
                candidato_norm = normalizar(m2.group(1).strip())
                candidato_limpo = re.sub(r"[^A-Z\s]", "", candidato_norm)
                if len(candidato_limpo.split()) >= 2:
                    return candidato_limpo

            # pega próxima linha não vazia
            j = i + 1
            while j < len(linhas) and not linhas[j].strip():
                j += 1
            if j < len(linhas):
                candidato = linhas[j].strip()
                candidato_norm = normalizar(candidato)
                candidato_limpo = re.sub(r"[^A-Z\s]", "", candidato_norm)
                return candidato_limpo if len(candidato_limpo.split()) >= 2 else None

    # 3) Fallback: procura todas as ocorrências de 'Nome' e prefere a última
    nome_matches = list(re.finditer(r"(?:Nome)\s*:??\s*(.+?)(?:\n|$)", texto, re.IGNORECASE))
    if nome_matches:
        # percorre de trás pra frente procurando a última ocorrência válida
        for mm in reversed(nome_matches):
            nome_raw = mm.group(1).strip()
            if re.search(r"[A-Za-zÀ-ú]", nome_raw):
                nome_norm = normalizar(nome_raw)
                nome = re.sub(r"[^A-Z\s]", "", nome_norm)
                if len(nome.split()) >= 2:
                    return nome

    # coluna: 'Nome' à esquerda e valor à direita (busca por linhas individuais)
    for ln in linhas:
        if re.search(r"\bNome\b", ln, re.IGNORECASE):
            parts = re.split(r"\s{2,}", ln)
            if len(parts) > 1:
                candidato = parts[-1].strip()
                if re.search(r"[A-Za-zÀ-ú]", candidato):
                    candidato_norm = normalizar(candidato)
                    candidato_limpo = re.sub(r"[^A-Z\s]", "", candidato_norm)
                    if len(candidato_limpo.split()) >= 2:
                        return candidato_limpo

    return None

def extrair_valor_correto(texto):
    if not texto:
        return None
    txt = texto.replace("\xa0", " ")
    txt = txt.replace("\n", " ")
    txt = re.sub(r"\s+", " ", txt)
    txt = re.sub(r"(?<=\d)\s+(?=\d{2}\b)", ",", txt)
    txt = re.sub(r"(?<=\d)\s+(?=\d{3}\b)", ".", txt)
    txt = re.sub(r"(?<=\d)\s+(?=\d)", "", txt)
    txt = re.sub(r"R\s*\$|R\s+S", "R$", txt, flags=re.IGNORECASE)
    match = re.search(r"(?:Valor|VALOR)\s*[:\-]?\s*(R\$\s*)?(\d+[.,]\d{2})", txt, re.IGNORECASE)
    if match:
        valor_encontrado = match.group(2)
        if match.group(1):
            valor_encontrado = "R$ " + valor_encontrado
        return valor_encontrado
    pattern = re.compile(r"(R\$\s*)?(\d+[.,]\d{2})", re.IGNORECASE)
    matches = list(pattern.finditer(txt))
    if matches:
        for m in matches:
            if m.group(1):
                val = m.group(2)
                return ("R$ " + val)
        for m in matches:
            start = max(0, m.start() - 40)
            contexto = txt[start:m.start()].upper()
            if "VALOR" in contexto or "TOTAL" in contexto or "R$" in contexto:
                return m.group(2)
        return matches[0].group(2)
    return None
# --- fim das funções incorporadas ---

DATA_DIR = "data"


def validar_data_no_texto(texto):
    if not texto:
        return None

    # Normaliza espaços não-quebreáveis e múltiplos espaços
    texto_limpo = texto.replace("\xa0", " ")
    texto_limpo = re.sub(r"\s+", " ", texto_limpo)

    # 1) Tenta primeiro padrão com dia da semana (específico do Inter): "segunda, 10/03/2025"
    m_dia_semana = re.search(PADRAO_DATA_COM_DIA_SEMANA, texto_limpo, re.IGNORECASE)
    if m_dia_semana:
        # Extrai a data do grupo 1 (DD/MM/YY ou DD/MM/YYYY)
        data_encontrada = m_dia_semana.group(1)
        # Converte DD/MM/YYYY para DD/MM/YY
        if re.match(r"\d{2}/\d{2}/\d{4}", data_encontrada):
            # "10/03/2025" -> "10/03/" ([:6]) + "25" ([-2:]) = "10/03/25"
            return data_encontrada[:6] + data_encontrada[-2:]
        if re.match(r"\d{2}/\d{2}/\d{2}", data_encontrada):
            return data_encontrada

    # 2) Tenta padrões reconhecidos normais
    m = re.search(PADRAO_DATA, texto_limpo, re.IGNORECASE)
    if m:
        # m may be tuple if pattern has groups; join into string
        found = m.group(0) if hasattr(m, 'group') else str(m)
        # tenta converter textual (DD MES AAAA)
        conv = converter_data_textual(found)
        if conv:
            return conv

        # normaliza formatação DD/MM/YY ou DD/MM/YYYY -> DD/MM/YY
        if re.match(r"\d{2}/\d{2}/\d{4}", found):
            return found[:6] + found[-2:]
        if re.match(r"\d{2}/\d{2}/\d{2}", found):
            return found

    return None


def processar_imagem(caminho_imagem, pessoas):
    resultado = {"arquivo": os.path.basename(caminho_imagem), "data": None, "valor": None, "nome": None, "id": None, "ok": False, "erro": None}

    if pytesseract is None:
        resultado["erro"] = "pytesseract não disponível"
        return resultado

    try:
        img = Image.open(caminho_imagem)
        texto = pytesseract.image_to_string(img, lang="por", config="--psm 6")

        # Modo debug: salvar texto OCR e os matches de valores para inspeção
        if os.environ.get("DEBUG_OCR"):
            debug_path = os.path.join(DATA_DIR, os.path.basename(caminho_imagem) + ".ocr.txt")
            with open(debug_path, "w", encoding="utf-8") as dbg:
                dbg.write(texto)
                dbg.write("\n\n--VALORES ENCONTRADOS PELO PADRAO--\n")
                dbg.write(str(re.findall(PADRAO_VALOR, texto)))

        # linhas para extrair nome com função existente
        linhas = [l.strip() for l in texto.splitlines() if l.strip()]

        nome = extrair_nome_do_texto(linhas)
        valor = extrair_valor_correto(texto)
        data = validar_data_no_texto(texto)
        hora = extrair_hora(texto)

        pid = achar_id(nome, pessoas) if nome else None

        resultado.update({"data": data, "valor": valor, "nome": nome, "id": pid, "hora": hora})

        # marca ok se encontrou data e valor (e idealmente id)
        resultado["ok"] = bool(data and valor)

    except Exception as e:
        resultado["erro"] = str(e)

    return resultado


def main():
    # Integração com API temporariamente comentada por solicitação.
    # pessoas = carregar_pessoas_api()
    # if not pessoas:
    #     print("Erro: API de pessoas retornou vazia ou falhou. A execução continuará sem mapeamento de IDs.")
    # Por enquanto, usa o CSV local como fonte de pessoas
    # Carrega pessoas exclusivamente do JSON local
    pessoas = carregar_pessoas_json()
    if not pessoas:
        print(f"Atenção: não foi possível carregar pessoas de {JSON_PESSOAS} ou arquivo vazio")
        pessoas = []

    if pytesseract is None:
        print("pytesseract não encontrado. Instale tesseract e torne-o acessível no PATH antes de rodar.")
        print("No Windows, instale Tesseract-OCR e adicione o diretório bin ao PATH.")
        return 1

    # Se houver argumentos de linha de comando, usa-os como nomes de imagem
    if len(sys.argv) > 1:
        arquivos = sys.argv[1:]
    else:
        # Caso contrário, lista todos os arquivos de imagem no diretório
        arquivos = [
            f for f in os.listdir(DATA_DIR)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

    for f in arquivos:
        caminho = os.path.join(DATA_DIR, f)
        r = processar_imagem(caminho, pessoas)

        # Spool no formato solicitado
        # Cleanup nome: remove accidental leading labels from OCR (e.g. 'NOME ', 'ORIGEM ')
        nome_raw = r.get('nome')
        if nome_raw:
            # strip and collapse spaces
            nome_clean = re.sub(r"\s+", " ", nome_raw).strip()
            # remove leading label words if present
            nome_clean = re.sub(r"^(NOME|ORIGEM)\s*:??\s*", "", nome_clean, flags=re.IGNORECASE)
            # converter para Title Case
            nome_clean = title_case(nome_clean)
        else:
            nome_clean = nome_raw

        print(f"*ID:* {r.get('id')}")
        print(f"*NOME:* {nome_clean}")
        print(f"*VALOR:* {r.get('valor')}")
        print(f"*DATA:* {r.get('data')}")
        print(f"*HORA:* {r.get('hora')}")
        if r.get("erro"):
            print(f"  ERRO: {r['erro']}")
        print()

        # Remover a imagem processada (restaura comportamento anterior)
        # Remove apenas se o processamento foi considerado OK
        try:
            if r.get("ok"):
                if os.path.exists(caminho):
                    os.remove(caminho)
        except Exception as e:
            print(f"Warning: não foi possível remover {caminho}: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())