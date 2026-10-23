# scrapladder

[![tests](https://github.com/CaiqueDourado/scrapladder/actions/workflows/tests.yml/badge.svg)](https://github.com/CaiqueDourado/scrapladder/actions/workflows/tests.yml)
[![Licença: MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

[Read in English](README.md)

![scrapladder](docs/img/cover.pt-BR.png)

Baixa uma página subindo uma escada de métodos, do mais barato ao mais pesado, e **lembra, por domínio, qual degrau funcionou**:

1. HTTP comum (`requests`, `httpx`);
2. HTTP com a impressão digital TLS de um navegador de verdade (`curl_cffi`);
3. navegadores headless (Playwright, Camoufox, Scrapling);
4. APIs de scraping pagas (ScraperAPI, ScrapingBee, ScrapingDog, Scrape.do) como último recurso.

A próxima URL do mesmo site começa no degrau que funcionou da última vez. Degraus bloqueados três vezes naquele site são pulados.

```python
from scrapladder import Ladder

with Ladder(memory="scrapladder.json") as ladder:
    r = ladder.fetch("https://loja.example.com.br/produto/123", must_contain="KZ ZSN Pro")

if r.ok:
    print(r.method, len(r.html))   # ex.: curl_cffi 184213
else:
    print(r.summary())             # ex.: blocked via - [curl_cffi:challenged(cloudflare_challenge) > playwright:challenged(...)]
```

## De onde vem

A escada é a camada de coleta do crawler por trás do site de análises de produtos do autor. Esse crawler lê páginas de fabricantes, reviews e preços de lojas brasileiras e de fora. Cada site se comporta de um jeito:

- uns respondem a qualquer cliente;
- outros devolvem `403` para todo cliente Python cujo handshake TLS não parece de navegador;
- outros só mostram o conteúdo depois que o JavaScript roda;
- outros param todo cliente automatizado já na CDN.

Testar todos os métodos em toda URL é lento e caro. Fixar um método por site quebra no dia em que o site muda.

Então o crawler passou a aprender. A memória dele chegou a 643 domínios. O gráfico mostra qual método pegou a página primeiro em cada um:

![Qual degrau pegou a página primeiro](docs/img/rungs.pt-BR.png)

- **curl_cffi** pegou a página em 480 domínios (75%). A maior parte dos "bloqueios" era só a impressão digital TLS.
- **Playwright** foi necessário em 70 domínios (11%), os sites que montam a página com JavaScript.
- **APIs pagas** resolveram 32 domínios (5%). Deixá-las por último manteve a conta baixa.

Ressalva sobre esses números: o crawler tentava `curl_cffi` antes de `httpx` e `requests`, então eles mostram qual degrau bastou, não que o HTTP comum teria falhado. A barra cinza é um método que o crawler tinha e esta biblioteca não inclui: ele usava o navegador do próprio autor, logado.

### O que a produção mostra

A memória só guarda o vencedor. O banco do crawler guarda cada página salva, então mostra mais.

**Páginas para pesquisa de produto** (reviews, sites de fabricante, fóruns): 6.869 páginas em 1.165 domínios, de setembro de 2025 a agosto de 2026.

| Método | Páginas | Domínios |
|---|---:|---:|
| Playwright | 2.018 (29%) | 385 |
| requests + BeautifulSoup (primeira versão, até out. 2025) | 1.799 (26%) | 392 |
| curl_cffi (escada, desde maio de 2026) | 1.616 (24%) | 463 |
| APIs pagas (ScraperAPI, ScrapingBee, Scrape.do, ScrapingDog) | 905 (13%) | — |
| navegador logado do autor (fora desta biblioteca) | 270 (4%) | 23 |
| httpx, DrissionPage, requests | 259 (4%) | — |

Das 11.892 URLs que terminaram (páginas e vídeos), 11.639 (97,9%) tiveram conteúdo, 119 (1,0%, em 36 domínios) ficaram bloqueadas e 35 não existiam mais (404).

**Preços de loja** são mais difíceis: 9.847 leituras de preço em páginas de produto de lojas brasileiras e de fora.

- **curl_cffi** pegou 25% delas.
- **requests** e **httpx** juntos pegaram 11%.
- **Navegadores** (Scrapling, DrissionPage) pegaram 9%.
- **APIs pagas** pegaram 7%.
- **O navegador logado do próprio autor** pegou 43%: os grandes marketplaces. Esta biblioteca não faz isso, então nesses sites espere `blocked` ou uma API paga.

## Como funciona

O que a memória aprende num site, URL após URL:

```mermaid
flowchart LR
  A["URL 1<br/>curl_cffi → desafio<br/>httpx → desafio<br/>playwright → ok"] --> M1[("loja.example.com.br<br/>vencedores: playwright<br/>bloqueios: curl_cffi 1, httpx 1")]
  M1 --> B["URL 2<br/>playwright → ok<br/>(1 requisição, não 3)"]
  B --> M2[("mesma memória<br/>depois de 3 bloqueios o degrau<br/>é pulado neste site")]
  M2 --> C["próxima execução<br/>lê o scrapladder.json<br/>e começa de onde parou"]
```

O que acontece com cada URL:

```mermaid
flowchart TD
  U["fetch(url)"] --> R{"robots.txt<br/>permite?"}
  R -- não --> D["disallowed"]
  R -- sim --> T["espera a vez do domínio<br/>min_interval, Retry-After"]
  T --> O["ordena os degraus<br/>vencedores → grátis por prioridade → pagos"]
  O --> M["próximo degrau"]
  M --> A{"resposta"}
  A -- "404 / 410" --> NF["not_found"]
  A -- "429" --> RL["rate_limited<br/>esfria o domínio"]
  A -- "bloqueio terminal<br/>Akamai, 403 de WAF" --> TB["terminal_block<br/>mesmo IP em todo degrau: para"]
  A -- "desafio<br/>Cloudflare, DataDome, CAPTCHA" --> C["conta um bloqueio para o degrau<br/>3 → pula no domínio"]
  A -- "página curta, texto ausente,<br/>timeout" --> M
  C --> M
  A -- "página de verdade" --> OK["ok<br/>esse degrau vai primeiro da próxima vez"]
```

| Degrau | Pacote | Prioridade | Para quê |
|---|---|---|---|
| `curl_cffi` | `curl_cffi` | 0,8 | HTTP com a impressão TLS/HTTP2 do Chrome (`impersonate`) |
| `httpx` | `httpx` (+`h2` para HTTP/2) | 0,65 | HTTP comum |
| `requests` | `requests` | 0,6 | HTTP comum |
| `playwright` | `playwright` | 0,4 | Chromium, roda JavaScript |
| `scrapling` | `scrapling` | 0,3 | `StealthyFetcher` do Scrapling |
| `camoufox` | `camoufox` | 0,3 | Firefox com impressão digital de usuário comum |
| `scrapedo`, `scrapingdog`, `scrapingbee`, `scraperapi` | `requests` + chave da API | 0,1, pago | IPs e navegadores deles, cobrado por requisição |

**Ordem.** Os vencedores do domínio vão primeiro. Depois vêm os degraus grátis, ordenados por uma prioridade aprendida em todos os domínios (média móvel dos últimos resultados, misturada com o padrão acima). Os pagos ficam por último, a menos que um deles já tenha vencido naquele domínio.

**Detecção de bloqueio** ([`blocks.py`](src/scrapladder/blocks.py)). Lê o status, os cabeçalhos e o começo do HTML, e separa o que encontra em três tipos:

| Tipo | Exemplos | Decisão |
|---|---|---|
| `terminal` | Akamai "Access Denied … edgesuite.net", página curta "403 Forbidden", incidente Imperva, Sucuri | para: todo degrau sai do mesmo IP |
| `challenge` | Cloudflare (`cf-mitigated`, "Just a moment…"), DataDome, PerimeterX, AWS WAF, reCAPTCHA/hCaptcha, "não é um robô" | conta um bloqueio para o degrau e tenta o próximo |
| `rate_limited` | HTTP 429, "too many requests" | para e respeita o `Retry-After` |

Só os primeiros 8.000 caracteres são lidos. Uma página de verdade que tem "too many requests" em algum script não é página de bloqueio.

**Checagens de conteúdo.** Um degrau que responde 200 não necessariamente pegou a página. Estas checagens recusam a resposta e passam para o próximo degrau:

- `min_length` (padrão: 500 caracteres);
- `must_contain`: o nome do produto, por exemplo. Pega o redirecionamento para a home ou a página "produto não encontrado";
- `accept(html)`: a sua própria checagem.

**Educação.**
- `min_interval` (padrão: 4 s) entre requisições ao mesmo domínio.
- Um 429 para a escada e esfria o domínio pelo tempo do `Retry-After`. Se a espera passar de `max_wait`, o `fetch` devolve `rate_limited` com `retry_after` em vez de dormir.
- O robots.txt é lido por padrão (`respect_robots=False` desliga).

**Memória.** Um JSON legível guarda os vencedores e os contadores de bloqueio de cada domínio e as estatísticas de cada método. É gravado de forma atômica. O formato antigo, `{"domínio": ["método", ...]}`, também é lido.

## Instalação

```bash
pip install "scrapladder[all] @ git+https://github.com/CaiqueDourado/scrapladder"
playwright install chromium           # para o degrau de navegador
pip install "scrapladder[camoufox]"   # opcional
pip install "scrapladder[scrapling]"  # opcional
```

Os extras são `http`, `curl`, `browser`, `camoufox` e `scrapling`; `all` junta os três primeiros. Degraus sem o pacote ou sem a chave da API ficam de fora. `scrapladder methods` mostra o que está disponível.

## Linha de comando

```bash
scrapladder methods                                   # quais degraus estão instalados
scrapladder explain https://loja.example.com.br/p/1   # testa TODOS os degraus, uma linha cada
scrapladder fetch https://loja.example.com.br/p/1 --memory scrapladder.json -o pagina.html
scrapladder stats --memory scrapladder.json           # qual degrau vence em quantos domínios
```

O `explain` é a ferramenta para um site novo: uma tabela com resultado, status, tamanho, tempo e motivo do bloqueio de cada degrau. Exemplo (ilustrativo):

```text
method       outcome         status      size    sec  reason
curl_cffi    ok                 200    184213    0.6
httpx        challenged         403      5871    0.3  cloudflare_challenge
requests     challenged         403      5871    0.2  cloudflare_challenge
playwright   ok                 200    402551    4.1
```

## Um degrau seu

```python
from scrapladder import Ladder
from scrapladder.methods import Method, Response, default_methods

class MinhaApiDeProxy(Method):
    name, default_priority, paid = "meuproxy", 0.2, True

    def fetch(self, url):
        r = meu_cliente.get(url)
        return Response(r.status, r.text, r.headers, r.url)

ladder = Ladder([*default_methods(), MinhaApiDeProxy()])
```

## Escopo

A scrapladder escolhe entre ferramentas públicas que já existem. Ela não:

- reaproveita cookies nem o perfil do seu navegador;
- faz login em sites;
- resolve CAPTCHA. Um CAPTCHA é registrado como `challenge` e a escada segue para o próximo degrau.

As opções dos backends (por exemplo `fetch_options` do Scrapling e `options` do Camoufox) são repassadas como vierem. O que você coleta, com que frequência e sob quais termos é responsabilidade sua.

## Limites

- A API síncrona do Playwright não é thread-safe: use uma `Ladder` por thread.
- As assinaturas de bloqueio são texto e cabeçalhos, e os fornecedores mudam as páginas deles. O `explain` e o `reason` de cada tentativa mostram quando falta uma assinatura; contribuições são bem-vindas.
- As prioridades aprendem com todos os domínios juntos. Um degrau ótimo em um site e ruim em muitos outros cai na ordem geral, mas os vencedores do próprio domínio ainda o colocam primeiro lá.

## Relacionados

- [transcriptladder](https://github.com/CaiqueDourado/transcriptladder): a mesma escada para transcrições do YouTube (legenda primeiro, reconhecimento de fala por último).
- [BrCommerceKit](https://github.com/CaiqueDourado/BrCommerceKit): detecta a plataforma de uma loja brasileira e lê o feed de produtos dela (um feed, quando existe, sai mais barato que qualquer degrau).
- [lojas-virtuais-brasil](https://github.com/CaiqueDourado/lojas-virtuais-brasil): 63.974 lojas virtuais brasileiras com a plataforma de cada uma.

## Licença

[MIT](LICENSE) © Caique Dourado
