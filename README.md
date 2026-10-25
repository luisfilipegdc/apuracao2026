# Eleições Brasil — Ao vivo e Histórico

App público com resultados eleitorais oficiais do TSE.

- **Ao vivo** (`index.html`): lê os arquivos JSON oficiais de divulgação do TSE em `resultados.tse.jus.br` durante a apuração. Para a próxima eleição, troque o ciclo e os códigos no topo do script (o TSE publica em https://www.tse.jus.br/eleicoes/informacoes-tecnicas-sobre-a-divulgacao-de-resultados).
- **Histórico** (`historico.html`): resultados desde 2000 por estado e município, lidos de `data/`.

## De onde vêm os dados do histórico

`scripts/etl_tse.py` baixa do Portal de Dados Abertos do TSE:
- `votacao_candidato_munzona_<ano>.zip` (votos por candidato, município e zona)
- `detalhe_votacao_munzona_<ano>.zip` (aptos, comparecimento, abstenção, brancos, nulos)

Granularidade: Presidente, Governador, Senador, Prefeito e Vereador por município; Deputados por estado.

A rotina **Atualizar dados do TSE** (GitHub Actions) roda manualmente e todo dia 1º do mês.
