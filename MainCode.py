import sys

import bs4
import requests

BASE = "https://ordemparanormal.fandom.com"
API = BASE + "/api.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (projeto didatico de web scraping - FATEC)"}


def _api(params):
    params = dict(params, format="json")
    res = requests.get(API, params=params, headers=HEADERS, timeout=15)
    print(f"[debug] {res.status_code} {res.url}")
    res.raise_for_status()
    return res.json()


def buscar_titulos(nome, limite=5):
    dados = _api({"action": "query", "list": "search",
                  "srsearch": nome, "srlimit": limite})
    titulos = [i["title"] for i in dados.get("query", {}).get("search", [])]
    if titulos:
        return titulos

    dados = _api({"action": "query", "list": "prefixsearch",
                  "pssearch": nome, "pslimit": limite})
    titulos = [i["title"] for i in dados.get("query", {}).get("prefixsearch", [])]
    if titulos:
        return titulos

    dados = _api({"action": "opensearch", "search": nome, "limit": limite})
    if isinstance(dados, list) and len(dados) > 1 and dados[1]:
        return dados[1]

    for tentativa in {nome, nome.title(), nome.capitalize()}:
        dados = _api({"action": "query", "titles": tentativa, "redirects": 1})
        paginas = dados.get("query", {}).get("pages", {})
        for pid, pag in paginas.items():
            if pid != "-1" and "missing" not in pag:
                return [pag["title"]]

    return []


def baixar_html(titulo):
    params = {
        "action": "parse",
        "page": titulo,
        "prop": "text",
        "redirects": 1,
        "format": "json",
    }
    res = requests.get(API, params=params, headers=HEADERS, timeout=15)
    res.raise_for_status()
    return res.json()["parse"]["text"]["*"]


def extrair_info(html):
    soup = bs4.BeautifulSoup(html, "html.parser")

    for sup in soup.select("sup"):
        sup.decompose()

    info = {"titulo": None, "dados": {}, "resumo": []}

    infobox = soup.select_one("aside.portable-infobox")
    if infobox:
        titulo = infobox.select_one(".pi-title")
        if titulo:
            info["titulo"] = titulo.get_text(" ", strip=True)

        for item in infobox.select("div.pi-item.pi-data"):
            rotulo = item.select_one(".pi-data-label")
            valor = item.select_one(".pi-data-value")
            if rotulo and valor:
                info["dados"][rotulo.get_text(" ", strip=True)] = valor.get_text(
                    " ", strip=True
                )

    for p in soup.select("div.mw-parser-output > p"):
        texto = p.get_text(" ", strip=True)
        if len(texto) > 40:
            info["resumo"].append(texto)
        if len(info["resumo"]) == 2:
            break

    return info


def mostrar(titulo_pagina, info):
    print("\n" + "=" * 60)
    print(info["titulo"] or titulo_pagina)
    print("=" * 60)

    if info["dados"]:
        for rotulo, valor in info["dados"].items():
            print(f"{rotulo}: {valor}")
        print()

    for paragrafo in info["resumo"]:
        print(paragrafo + "\n")

    if not info["dados"] and not info["resumo"]:
        print("Não consegui extrair informações desta página.")

    print("Link:", f"{BASE}/wiki/{titulo_pagina.replace(' ', '_')}")


def escolher_titulo(nome):
    titulos = buscar_titulos(nome)
    if not titulos:
        print("Nenhum resultado encontrado.")
        return None
    if len(titulos) == 1:
        return titulos[0]

    print("\nResultados encontrados:")
    for i, t in enumerate(titulos, 1):
        print(f"  {i}) {t}")
    escolha = input("Escolha um número (Enter = 1): ").strip()
    if escolha.isdigit() and 1 <= int(escolha) <= len(titulos):
        return titulos[int(escolha) - 1]
    return titulos[0]


def processar(nome):
    try:
        titulo = escolher_titulo(nome)
        if not titulo:
            return
        info = extrair_info(baixar_html(titulo))
        mostrar(titulo, info)

    except requests.exceptions.RequestException as exc:
        print("Problema de conexão/requisição:", exc)
    except (KeyError, ValueError) as exc:
        print("Resposta inesperada do site:", exc)


def main():
    em_notebook = "ipykernel" in sys.modules or "google.colab" in sys.modules
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if args and not em_notebook:
        processar(" ".join(args))
        return

    print("Ordem Paranormal Wiki - busca de personagens (digite 'sair' para fechar)")
    while True:
        nome = input("\nNome do personagem: ").strip()
        if nome.lower() in ("sair", "exit", "q"):
            break
        if nome:
            processar(nome)


if __name__ == "__main__":
    main()
