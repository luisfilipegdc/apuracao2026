# Eleições Brasil (nome provisório)

Plataforma pública de dados eleitorais do Brasil: apuração ao vivo e memória eleitoral desde 2000.
Objetivo: ser melhor que o Radar do Voto (radardovoto.com) em velocidade, clareza no celular,
compartilhamento, comparação cidade × cidade e apuração sem atraso. Ler `docs/prompt-claude-code.md`.

## Regras que não mudam
- Só dados oficiais (TSE, IBGE). Nunca inventar, estimar sem rotular ou "completar" número.
- Toda tela que mostra número diz a fonte (arquivo e data de geração).
- Mobile first: tudo funciona em 390px antes de pensar no desktop. Sem rolagem lateral.
- Português do Brasil, frases curtas, sem jargão. Nada de pop-up, cadastro obrigatório ou banner de doação.
- Sem segredos no repositório. Variáveis sensíveis só em `.env` na VPS ou nas variáveis da Vercel.

## Estrutura atual
- `index.html` home com busca de município · `municipio.html?cd=&uf=` Raio-X da cidade
- `aovivo.html` apuração (abas #presidente #estados #governadores) · `historico.html` consulta por eleição
- `assets/app.css` design system (tokens no topo) · `assets/common.js` utilidades compartilhadas
- `scripts/etl_tse.py` ETL dos Dados Abertos → `data/` (JSON estáticos)
- `.github/workflows/dados-tse.yml` roda o ETL no GitHub Actions
- `vercel.json` atalho `/tse/*` → resultados.tse.jus.br/oficial/* com cache de 15 s na Vercel

## Armadilhas conhecidas do TSE
- Divulgação ao vivo: limite de 100 req/s por IP, bloqueio de 10 min; muitos 404 também bloqueiam. Código de município com 5 dígitos.
- Códigos 2026: 1º turno 6257 (federal) 6259 (estadual); 2º turno 6258 / 6260. Arquivos de 2022 já saíram do CDN de divulgação.
- Dados Abertos (cdn.tse.jus.br/estatistica/sead/odsele/...): latin-1, separador `;`, use o arquivo `_BRASIL.csv` do zip;
  coluna de votos varia (`QT_VOTOS_NOMINAIS_VALIDOS` ou `QT_VOTOS_NOMINAIS`); filtre `CD_TIPO_ELEICAO == 2` (ordinária).
  O CDN responde "Access Denied" a robôs/excesso de pedidos: baixe devagar, com retentativa, nunca burlando bloqueio.
