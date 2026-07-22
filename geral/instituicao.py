import re
import unicodedata
import os
import sys

try:
    from PIL import Image
    import pytesseract
except Exception:
    pytesseract = None

try:
    import pdfplumber
except Exception:
    pdfplumber = None
    
if sys.platform == "win32":
    PASTA_IMAGENS = r"C:\Users\brunoquaiatti\Documents\GitHub\gazofilacio-scripts\geral"
else:
    PASTA_IMAGENS = "/home/node/data/"

def normalizar(txt):
    if not txt:
        return ""
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return txt.upper().strip()


# Padrões de identificação de instituições
INSTITUICOES = {
    "NUBANK": {
        "keywords": [
            r"\bNUBANK\b",
            r"\bNU\s*PAGAMENTOS\b",
            r"NU PAGAMENTOS S\.A\.",
        ],
        "score": 100
    },
    "BRADESCO": {
        "keywords": [
            r"\bBANDESCO\b",
            r"\bBRADESCO\b",
            r"BANCO BRADESCO",
        ],
        "score": 90
    },
    "ITAU": {
        "keywords": [
            r"ITAÚ\s+UNIBANCO\s+S\.A",
            r"ITAU\s+UNIBANCO\s+S\.A",
            r"ITAÚ\s+UNIBANCO",
            r"ITAU\s+UNIBANCO",
            r"\bITAÚ\b",
            r"\bITAU\b",
            r"BANCO ITAU",
        ],
        "score": 90
    },
    "CAIXA": {
        "keywords": [
            r"CAIXA\s+ECONOMICA\s+FEDERAL",
            r"CAIXA\s+ECONOMICA\s+S\.A",
            r"CAIXA\s+ECONOMICA",
            r"CEF\s+S\.A",
            r"\bCEF\b",
            r"CAIXA\s+ECO",
            r"CAIXA\s+FEDERAL",
            r"\bCAIXA\b",
        ],
        "score": 95
    },
    "SANTANDER": {
        "keywords": [
            r"BANCO\s+SANTANDER\s*\(\s*BRASIL\s*\)\s*S\.A",
            r"BCO\s+SANTANDER",
            r"BANCO\s+SANTANDER",
            r"\bSANTANDER\b",
        ],
        "score": 90
    },
    "SICREDI": {
        "keywords": [
            r"BANCO\s+SICREDI\s+S\.A",
            r"SICREDI\s+S\.A",
            r"SICREDI\s+LTDA",
            r"BANCO\s+SICREDI",
            r"\bSICREDI\b",
        ],
        "score": 95
    },
    "BB": {
        "keywords": [
            r"\bBB\b",
            r"BANCO\s+DO\s+BRASIL\s+S\.A",
            r"BCO\s+DO\s+BRASIL\s+S\.A",
            r"BANCO DO BRASIL",
            r"BANCO\s+DO\s+BRASIL",
            r"BCO DO BRASIL",
        ],
        "score": 90
    },
    "INTER": {
        "keywords": [
            r"\bINTER\b",
            r"BANCO INTER",
            r"BANCO INTER S\.A",
            r"INTER S\.A",
        ],
        "score": 95
    },
    "PICPAY": {
        "keywords": [
            r"PICPAY\s*S\.A",
            r"PICPAY\s*LTDA",
            r"\bPICPAY\b",
            r"PIC\s*PAY",
            r"PICPAYBANK",
        ],
        "score": 95
    },
    "MERCADOPAGO": {
        "keywords": [
            r"MERCADO\s+PAGO",
            r"MERCADOPAGO",
            r"MERCADOPAGO\s+S\.A",
            r"MERCADO PAGO S\.A",
        ],
        "score": 95
    },
    "C6": {
        "keywords": [
            r"\bC6\s+BANK\b",
            r"\bC6\s+S\.A\b",
            r"C6\s+BANCO",
            r"\bC6\b",
        ],
        "score": 95
    },
    "PAYPAL": {
        "keywords": [
            r"\bPAYPAL\b",
            r"PAY\s*PAL",
        ],
        "score": 90
    },
    "STRIPE": {
        "keywords": [
            r"\bSTRIPE\b",
        ],
        "score": 90
    },
    "XP": {
        "keywords": [
            r"BANCO\s+XP\s+S\.A",
            r"BANCO\s+XP",
            r"\bBCO\s+XP\b",
            r"\bXP\s+S\.A\b",
            r"\bXP\b",
        ],
        "score": 95
    },
    "PAGBANK": {
        "keywords": [
            r"PAGBANK\s*\(\s*PAGSEGURO\s+INTERNET\s+INSTITUICAO\s+DE\s+PAGAMENTO\s+S\.A",
            r"PAGBANK\s*\(\s*PAGSEGURO\s*\)",
            r"PAGSEGURO\s+INTERNET\s+INSTITUICAO\s+DE\s+PAGAMENTO",
            r"PAGBANK",
            r"PAG\s*BANK",
        ],
        "score": 95
    },
}


def extrair_instituicao(texto):
    """
    Extrai a instituição financeira do texto OCR de um comprovante.
    Padrões mais específicos (com S.A, PAGAMENTOS, etc) têm prioridade.
    
    Args:
        texto (str): Texto extraído via OCR do comprovante
    
    Returns:
        dict: {'instituicao': <str>, 'confianca': <float>}
    """
    if not texto:
        return {"instituicao": None, "confianca": 0.0}
    
    texto_norm = normalizar(texto)
    melhor_match = None
    melhor_score = -1
    
    for instituicao, config in INSTITUICOES.items():
        # Tenta cada padrão, priorizando os mais específicos (compridos)
        patterns_com_score = [(pattern, len(pattern)) for pattern in config["keywords"]]
        patterns_com_score.sort(key=lambda x: x[1], reverse=True)  # Ordena por comprimento (mais específico primeiro)
        
        for pattern, pattern_len in patterns_com_score:
            if re.search(pattern, texto_norm, re.IGNORECASE):
                # Bonus para padrões mais específicos
                especificidade_bonus = pattern_len // 10  # Quanto mais longo, mais bonus
                score_total = config["score"] + especificidade_bonus
                
                if score_total > melhor_score:
                    melhor_score = score_total
                    melhor_match = instituicao
                
                break  # Found match for this instituição, move to next
    
    if melhor_match:
        # Confiança: percentual baseado no score
        confianca = min(100, melhor_score) / 100.0
        return {"instituicao": melhor_match, "confianca": confianca}
    
    return {"instituicao": None, "confianca": 0.0}


def extrair_instituicao_do_texto(linhas):
    """
    Extrai a instituição do texto buscando em seções de origem (pagador).
    Procura por "Dados do pagador" e extrai a instituição listada nessa seção.
    
    Args:
        linhas (list): Lista de linhas de texto do OCR
    
    Returns:
        dict: {'instituicao': <str>, 'confianca': <float>}
    """
    if not linhas:
        return {"instituicao": None, "confianca": 0.0}
    
    # Encontra a seção de dados do pagador
    idx_pagador = -1
    
    for i, ln in enumerate(linhas):
        ln_norm = normalizar(ln)
        if "DADOS DO PAGADOR" in ln_norm:
            idx_pagador = i
            break  # Pega a primeira ocorrência
    
    # Se encontrou "Dados do pagador", procura a instituição nessa seção
    if idx_pagador != -1:
        # Procura por "Instituição" após "Dados do pagador"
        for i in range(idx_pagador, len(linhas)):
            ln = linhas[i]
            ln_norm = normalizar(ln)
            
            # Se encontrou "Instituição"
            if "INSTITUICAO" in ln_norm:
                # Tenta extrair da mesma linha
                m = re.search(r"(?:Instituição|INSTITUIÇÃO)\s*:?\s*(.+)$", ln, re.IGNORECASE)
                if m and m.group(1).strip():
                    candidato = m.group(1).strip()
                    result = extrair_instituicao(candidato)
                    if result["instituicao"]:
                        return result
                
                # Ou pega da próxima linha não vazia
                j = i + 1
                while j < len(linhas) and not linhas[j].strip():
                    j += 1
                
                if j < len(linhas):
                    candidato = linhas[j].strip()
                    # Verifica se não é outro campo
                    if candidato and not re.search(r"^(?:CPF|CNPJ|Chave|De|Para|Dados|ID)", candidato, re.IGNORECASE):
                        result = extrair_instituicao(candidato)
                        if result["instituicao"]:
                            return result
                break  # Para na primeira "Instituição" encontrada após "Dados do pagador"
    
    # Fallback: procura em todo o texto
    texto = "\n".join(linhas)
    result = extrair_instituicao(texto)
    return result


def extrair_texto_pdf(caminho_pdf):
    """
    Extrai texto de um arquivo PDF.
    
    Args:
        caminho_pdf (str): Caminho para o arquivo PDF
    
    Returns:
        list: Lista de linhas de texto extraído
    """
    if pdfplumber is None:
        return []
    
    try:
        texto_completo = ""
        with pdfplumber.open(caminho_pdf) as pdf:
            for page in pdf.pages:
                texto_completo += page.extract_text() + "\n"
        
        linhas = [l.strip() for l in texto_completo.splitlines() if l.strip()]
        return linhas
    except Exception:
        return []


if __name__ == "__main__":
    if pytesseract is None and pdfplumber is None:
        print("pytesseract e pdfplumber não disponíveis")
        exit(1)
    
    # Se houver argumentos de linha de comando, usa-os como nomes de arquivo
    if len(sys.argv) > 1:
        arquivos = sys.argv[1:]
    else:
        # Caso contrário, lista todos os arquivos (imagens e PDFs) no diretório
        if not os.path.exists(PASTA_IMAGENS):
            print(f"Pasta {PASTA_IMAGENS} não existe")
            exit(1)
        
        arquivos = [
            f for f in os.listdir(PASTA_IMAGENS)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".pdf"))
        ]
    
    if not arquivos:
        print(f"Nenhum arquivo encontrado")
        exit(0)
    
    for f in arquivos:
        # Se o arquivo foi passado como argumento, pode ser um caminho completo ou só o nome
        if os.path.isabs(f) or os.path.exists(f):
            caminho = f
        else:
            caminho = os.path.join(PASTA_IMAGENS, f)
        
        try:
            linhas = []
            
            # Verifica se é PDF ou imagem
            if f.lower().endswith(".pdf"):
                if pdfplumber is None:
                    print(f"{os.path.basename(f)}: ERRO - pdfplumber não disponível")
                    continue
                linhas = extrair_texto_pdf(caminho)
            else:
                if pytesseract is None:
                    print(f"{os.path.basename(f)}: ERRO - pytesseract não disponível")
                    continue
                img = Image.open(caminho)
                texto = pytesseract.image_to_string(img, lang="por", config="--psm 6")
                linhas = [l.strip() for l in texto.splitlines() if l.strip()]
            
            if linhas:
                resultado = extrair_instituicao_do_texto(linhas)
                print(f"{os.path.basename(f)}: {resultado.get('instituicao')}")
            else:
                print(f"{os.path.basename(f)}: ERRO - Nenhum texto extraído")
        except Exception as e:
            print(f"{os.path.basename(f)}: ERRO - {e}")
