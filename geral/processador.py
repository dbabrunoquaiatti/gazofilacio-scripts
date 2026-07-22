#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Processador central que identifica a instituição de um comprovante 
e usa o módulo apropriado para extração de dados.
"""

import os
import sys
import json
import importlib
from PIL import Image
import pytesseract

from instituicao import extrair_instituicao_do_texto

# Mapeamento de instituição para módulo Python
MAPA_INSTITUICAO_MODULO = {
    "BB": "bb",
    "BRADESCO": "bradesco",
    "CAIXA": "caixa",
    "C6": "c6",
    "INTER": "inter",
    "ITAU": "itau",
    "MERCADOPAGO": "mercadopago",
    "NUBANK": "nubank",
    "PAGBANK": "pagbank",
    "PICPAY": "picpay",
    "SANTANDER": "santander",
    "SICREDI": "sicredi",
    "XP": "xp",
    "PAYPAL": None,  # Não possui módulo específico
    "STRIPE": None,  # Não possui módulo específico
}

from config import PASTA_INST as PASTA_IMAGENS, JSON_PESSOAS

def processar_comprovante(caminho_arquivo, pessoas):
    """
    Processa um comprovante de forma universal.
    
    Args:
        caminho_arquivo (str): Caminho para o arquivo (JPEG, PNG, ou PDF)
        pessoas (list): Lista de dicts com informações de pessoas
        
    Returns:
        dict: Resultado do processamento com os dados extraídos
    """
    resultado = {
        "arquivo": os.path.basename(caminho_arquivo),
        "instituicao": None,
        "confianca_instituicao": 0.0,
        "data": None,
        "valor": None,
        "nome": None,
        "id": None,
        "ok": False,
        "erro": None,
        "modulo_usado": None
    }
    
    try:
        # Extrai texto da imagem ou PDF
        if caminho_arquivo.lower().endswith(".pdf"):
            try:
                import pdfplumber
                texto_completo = ""
                with pdfplumber.open(caminho_arquivo) as pdf:
                    for page in pdf.pages:
                        texto_completo += page.extract_text() + "\n"
                texto = texto_completo
            except ImportError:
                resultado["erro"] = "pdfplumber não disponível"
                return resultado
        else:
            # Processa imagem
            if pytesseract is None:
                resultado["erro"] = "pytesseract não disponível"
                return resultado
            
            img = Image.open(caminho_arquivo)
            texto = pytesseract.image_to_string(img, lang="por", config="--psm 6")
        
        # Extrai linhas
        linhas = [l.strip() for l in texto.splitlines() if l.strip()]
        
        if not linhas:
            resultado["erro"] = "Nenhum texto extraído do arquivo"
            return resultado
        
        # Identifica a instituição
        resultado_instituicao = extrair_instituicao_do_texto(linhas)
        resultado["instituicao"] = resultado_instituicao.get("instituicao")
        resultado["confianca_instituicao"] = resultado_instituicao.get("confianca", 0.0)
        
        if not resultado["instituicao"]:
            resultado["erro"] = "Instituição não identificada"
            return resultado
        
        # Obtém o nome do módulo
        nome_modulo = MAPA_INSTITUICAO_MODULO.get(resultado["instituicao"])
        
        if not nome_modulo:
            resultado["erro"] = f"Nenhum módulo configurado para {resultado['instituicao']}"
            return resultado
        
        # Importa o módulo dinamicamente
        try:
            modulo = importlib.import_module(nome_modulo)
            resultado["modulo_usado"] = nome_modulo
        except ImportError as e:
            resultado["erro"] = f"Não foi possível carregar módulo {nome_modulo}: {e}"
            return resultado
        
        # Chama a função processar_imagem do módulo
        if not hasattr(modulo, "processar_imagem"):
            resultado["erro"] = f"Módulo {nome_modulo} não possui função processar_imagem"
            return resultado
        
        # Processa com o módulo específico
        resultado_modulo = modulo.processar_imagem(caminho_arquivo, pessoas)
        
        # Mescla resultados
        resultado.update(resultado_modulo)
        resultado["modulo_usado"] = nome_modulo
        resultado["instituicao"] = resultado_instituicao.get("instituicao")
        resultado["confianca_instituicao"] = resultado_instituicao.get("confianca", 0.0)
        
    except Exception as e:
        resultado["erro"] = str(e)
    
    return resultado


def processar_diretorio(diretorio, pessoas):
    """
    Processa todos os comprovantes de um diretório.
    
    Args:
        diretorio (str): Caminho do diretório
        pessoas (list): Lista de pessoas
        
    Returns:
        list: Lista de resultados de processamento
    """
    resultados = []
    
    if not os.path.isdir(diretorio):
        print(f"Erro: Diretório {diretorio} não existe")
        return resultados
    
    exts = (".jpg", ".jpeg", ".png", ".pdf")
    arquivos = [f for f in os.listdir(diretorio) if f.lower().endswith(exts)]
    
    if not arquivos:
        print(f"Nenhum arquivo encontrado em {diretorio}")
        return resultados
    
    for arquivo in sorted(arquivos):
        caminho = os.path.join(diretorio, arquivo)
        print(f"Processando: {arquivo}...", end=" ", flush=True)
        
        resultado = processar_comprovante(caminho, pessoas)
        resultados.append(resultado)
        
        if resultado["ok"]:
            print(f"✓ ({resultado['instituicao']})")
        else:
            print(f"✗ Erro: {resultado.get('erro', 'Desconhecido')}")
    
    return resultados


def main():
    """Função principal para testes."""
    # Carrega pessoas
    try:
        with open(JSON_PESSOAS, encoding="utf-8") as f:
            pessoas_data = json.load(f)
            if isinstance(pessoas_data, list):
                pessoas = pessoas_data
            elif isinstance(pessoas_data, dict) and "data" in pessoas_data:
                pessoas = pessoas_data["data"]
            else:
                pessoas = []
    except Exception:
        print("Aviso: Não foi possível carregar pessoas.json")
        pessoas = []
    
    # Processa imagens
    print(f"Começando processamento...")
    print(f"Carregadas {len(pessoas)} pessoas\n")
    
    if len(sys.argv) > 1:
        # Processa arquivo específico
        for arquivo in sys.argv[1:]:
            print(f"\n=== {os.path.basename(arquivo)} ===")
            resultado = processar_comprovante(arquivo, pessoas)
            print(f"Instituição: {resultado['instituicao']} (confiança: {resultado['confianca_instituicao']:.2f})")
            print(f"Módulo: {resultado['modulo_usado']}")
            print(f"Data: {resultado['data']}")
            print(f"Valor: {resultado['valor']}")
            print(f"Nome: {resultado['nome']}")
            print(f"ID: {resultado['id']}")
            print(f"OK: {resultado['ok']}")
            if resultado['erro']:
                print(f"Erro: {resultado['erro']}")
    else:
        # Processa todo o diretório
        resultados = processar_diretorio(PASTA_IMAGENS, pessoas)
        
        print(f"\n\n=== RESUMO ===")
        print(f"Total processado: {len(resultados)}")
        print(f"Sucesso: {sum(1 for r in resultados if r['ok'])}")
        print(f"Erro: {sum(1 for r in resultados if not r['ok'])}")
        
        # Agrupa por instituição
        print(f"\n=== POR INSTITUIÇÃO ===")
        por_instituicao = {}
        for r in resultados:
            inst = r['instituicao'] or 'Desconhecida'
            if inst not in por_instituicao:
                por_instituicao[inst] = {"total": 0, "sucesso": 0}
            por_instituicao[inst]["total"] += 1
            if r['ok']:
                por_instituicao[inst]["sucesso"] += 1
        
        for inst in sorted(por_instituicao.keys()):
            stats = por_instituicao[inst]
            print(f"{inst:20} {stats['sucesso']}/{stats['total']} sucesso(s)")


if __name__ == "__main__":
    sys.exit(main() or 0)
