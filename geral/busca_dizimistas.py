#!/usr/bin/env python3
import sys
import json
import difflib
import os
import requests

API_URL = "https://hkcbddzaurlkopeypkgm.supabase.co/functions/v1/api-gateway/dizimistas"
TOKEN = "45ce65e6ac089bed6cbead711bb6fc170ed40f5a55d8df75ec046438a8232521"
PESSOAS_FILE = os.path.join(os.path.dirname(__file__), "pessoas.json")

def buscar_por_alias(alias):
    try:
        headers = {"X-API-Key": TOKEN}
        response = requests.get(API_URL, headers=headers, params={"alias": alias, "status": "ativo"})
        response.raise_for_status()
        data = response.json()
        resultados = data.get("data", data)
        return resultados if resultados else None
    except requests.exceptions.RequestException:
        return None

def buscar_por_nome(nome):
    try:
        headers = {"X-API-Key": TOKEN}
        response = requests.get(API_URL, headers=headers, params={"nome": nome, "status": "ativo"})
        response.raise_for_status()
        data = response.json()
        resultados = data.get("data", data)
        return resultados if resultados else None
    except requests.exceptions.RequestException:
        return None

def buscar_todos():
    """Busca todos os dizimistas ativos paginando de 10 em 10 e salva em pessoas.json."""
    headers = {"X-API-Key": TOKEN}
    todos = []
    offset = 0
    limit = 10

    while True:
        try:
            params = {"status": "ativo", "limit": limit, "offset": offset}
            response = requests.get(API_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            pagina = data.get("data", data)

            if not pagina:
                break

            _campos = ("nome_completo", "alias", "codigo_dizimista")
            todos.extend({k: p[k] for k in _campos if k in p} for p in pagina)

            if len(pagina) < limit:
                break

            offset += limit

        except requests.exceptions.RequestException:
            break

    if todos:
        with open(PESSOAS_FILE, "w", encoding="utf-8") as f:
            json.dump(todos, f, ensure_ascii=False, indent=2)

    return todos if todos else None

_PALAVRAS_IGNORADAS = {"de", "da", "do", "dos", "das", "e"}

def _score_proximidade(nome_busca, nome_candidato):
    a = nome_busca.lower()
    b = nome_candidato.lower()

    palavras_busca = set(a.split()) - _PALAVRAS_IGNORADAS
    palavras_candidato = set(b.split()) - _PALAVRAS_IGNORADAS
    palavras_comuns = palavras_busca & palavras_candidato

    # exige pelo menos 2 palavras significativas em comum
    if len(palavras_comuns) < 2:
        return 0.0

    cobertura = len(palavras_comuns) / len(palavras_busca) if palavras_busca else 0
    ratio = difflib.SequenceMatcher(None, a, b).ratio()

    return 0.4 * ratio + 0.6 * cobertura

def buscar_por_proximidade(nome_busca, pessoas, top=3, threshold=0.5):
    """Encontra os melhores matches por proximidade de nome."""
    scored = []
    for p in pessoas:
        nome_candidato = p.get("nome_completo", "")
        if not nome_candidato:
            continue
        score = _score_proximidade(nome_busca, nome_candidato)
        if score >= threshold:
            scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:top]]

def _carregar_ou_buscar_todos():
    """Sempre busca versão atualizada e salva em pessoas.json."""
    return buscar_todos()

def buscar_dizimista(nome):
    """Pipeline completo: 1) alias  2) nome  3) proximidade via pessoas.json."""
    resultados = buscar_por_alias(nome)
    if not resultados:
        resultados = buscar_por_nome(nome)
    if not resultados:
        todos = _carregar_ou_buscar_todos()
        if todos:
            resultados = buscar_por_proximidade(nome, todos)
    return resultados or None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python busca_dizimistas.py <nome>")
        sys.exit(1)

    nome = sys.argv[1]
    print(f"Buscando: {nome}...")

    resultados = buscar_dizimista(nome)

    if resultados:
        for r in resultados:
            print(f"  Código: {r.get('codigo_dizimista')} | Nome: {r.get('nome_completo')} | Alias: {r.get('alias')}")
    else:
        print("Nenhum resultado encontrado.")
