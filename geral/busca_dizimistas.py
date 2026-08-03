#!/usr/bin/env python3
import sys
import requests

API_URL = "https://hkcbddzaurlkopeypkgm.supabase.co/functions/v1/api-gateway/dizimistas"
TOKEN = "45ce65e6ac089bed6cbead711bb6fc170ed40f5a55d8df75ec046438a8232521"

def buscar_por_alias(alias):
    try:
        headers = {"X-API-Key": TOKEN}
        response = requests.get(API_URL, headers=headers, params={"alias": alias})
        response.raise_for_status()

        data = response.json()
        resultados = data.get("data", data)
        return resultados if resultados else None

    except requests.exceptions.RequestException:
        return None

def buscar_por_nome(nome):
    try:
        headers = {"X-API-Key": TOKEN}
        response = requests.get(API_URL, headers=headers, params={"nome": nome})
        response.raise_for_status()

        data = response.json()
        resultados = data.get("data", data)
        return resultados if resultados else None

    except requests.exceptions.RequestException:
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python busca_dizimistas.py <nome>")
        sys.exit(1)

    nome = sys.argv[1]
    print(f"Buscando: {nome}...")

    resultados = buscar_por_alias(nome)

    if resultados is None:
        print("Fallback: buscando por nome...")
        resultados = buscar_por_nome(nome)

    if resultados is None:
        print("Erro ao buscar.")
    elif len(resultados) == 0:
        print("Nenhum resultado encontrado.")
    else:
        for r in resultados:
            print(f"  Código: {r.get('codigo_dizimista')} | Nome: {r.get('nome_completo')} | Alias: {r.get('alias')}")
