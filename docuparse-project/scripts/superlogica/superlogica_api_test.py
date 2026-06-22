import json
import sys

import requests

BASE_URL = "https://api.superlogica.net/v2/condor"
APP_TOKEN = "ce25cb30-d6b5-471a-ba9a-d72f3b0ccbb3"
ACCESS_TOKEN = "82100fe9-8002-44a7-869b-93e494d010c8"

HEADERS = {
    "Content-Type": "application/json",
    "app_token": APP_TOKEN,
    "access_token": ACCESS_TOKEN,
}


def test_plano_contas(id_condominio: int = -1):
    url = f"{BASE_URL}/planocontas/index/"
    params = {"ID_CONDOMINIO_COND": id_condominio}

    print("=" * 60)
    print("TESTE: Listar Planos de Contas")
    print("=" * 60)
    print(f"URL:    {url}")
    print(f"Params: {params}")
    print("-" * 60)

    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=30)
    except requests.exceptions.ConnectionError as e:
        print(f"ERRO DE CONEXAO: Nao foi possivel conectar ao servidor.")
        print(f"  Detalhe: {e}")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("ERRO: A requisicao excedeu o tempo limite (30s).")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"ERRO INESPERADO NA REQUISICAO: {e}")
        sys.exit(1)

    print(f"Status HTTP: {response.status_code} {response.reason}")
    print("-" * 60)

    if not response.ok:
        print(f"FALHA: O servidor retornou um erro.")
        print(f"  Status: {response.status_code}")
        try:
            error_body = response.json()
            print(f"  Corpo da resposta:")
            print(json.dumps(error_body, indent=2, ensure_ascii=False))
        except ValueError:
            print(f"  Corpo da resposta (texto): {response.text}")
        sys.exit(1)

    try:
        data = response.json()
    except ValueError:
        print("ERRO: A resposta nao e um JSON valido.")
        print(f"  Corpo recebido: {response.text}")
        sys.exit(1)

    print("SUCESSO: Resposta recebida.")
    print(f"  Tipo dos dados: {type(data).__name__}")

    if isinstance(data, list):
        print(f"  Total de registros: {len(data)}")
        if data:
            print("\nPrimeiro registro (exemplo):")
            print(json.dumps(data[0], indent=2, ensure_ascii=False))
    else:
        print("\nResposta completa:")
        print(json.dumps(data, indent=2, ensure_ascii=False))

    print("=" * 60)
    return data


if __name__ == "__main__":
    test_plano_contas(id_condominio=-1)
