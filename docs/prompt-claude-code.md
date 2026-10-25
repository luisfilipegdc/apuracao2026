# Prompt para o Claude Code — Eleições Brasil

Cole tudo abaixo no Claude Code, com o repositório `luisfilipegdc/apuracao2026` aberto.

---

Você vai evoluir o repositório `apuracao2026` para uma plataforma pública de dados eleitorais do Brasil,
melhor que o Radar do Voto (radardovoto.com). Leia `CLAUDE.md` antes de tudo e siga as regras dele.

## Contexto
- Hoje existe um site estático na Vercel (https://apuracao2026-nu.vercel.app) com: home de busca de município,
  Raio-X da cidade, apuração ao vivo e consulta histórica. O histórico usa JSON gerados por `scripts/etl_tse.py`,
  mas a carga real ainda não foi validada em produção.
- Tenho uma VPS Ubuntu com Docker, 8 GB+ de RAM e mais de 100 GB livres. Ainda não tenho domínio para o projeto
  (posso usar um subdomínio de um domínio meu; pergunte qual antes de configurar).
- O Radar do Voto já cobre 1933–2026, voto por bairro e escola, comparativo de candidatos, emendas e doadores,
  planos a partir de R$47. Nosso diferencial NÃO é volume de dados. É:
  1. velocidade (página de cidade abre em menos de 1 s no 4G);
  2. clareza no celular (uma pergunta por tela, sem pop-up, sem cadastro);
  3. compartilhamento (imagem pronta para Instagram/WhatsApp de cada resultado);
  4. comparação cidade × cidade e cidade × estado;
  5. apuração ao vivo direto do TSE, sem atraso.

## Arquitetura alvo
- **Vercel**: só a interface (HTML/CSS/JS sem framework pesado; pode usar Preact/htm via CDN se ajudar).
- **VPS** (Docker Compose):
  - `etl`: baixa Dados Abertos do TSE e APIs do IBGE, grava em **DuckDB** (arquivo) e exporta Parquet.
  - `api`: FastAPI lendo o DuckDB, respostas JSON pequenas e com `Cache-Control`/`CDN-Cache-Control`.
  - `caddy`: HTTPS automático no subdomínio da API.
- A Vercel encaminha `/api/*` para a VPS por rewrite em `vercel.json`, com cache na Vercel.
  Proteja a origem com o cabeçalho secreto descrito em https://vercel.com/docs/rewrites
  ("Restricting your origin to Vercel traffic"). O segredo fica em variável de ambiente, nunca no repositório.
- Mantenha o atalho `/tse/*` já existente para o ao vivo.

## Fontes de dados (só estas, nesta ordem de prioridade)
1. TSE Dados Abertos — https://dadosabertos.tse.jus.br (arquivos em cdn.tse.jus.br/estatistica/sead/odsele/):
   `votacao_secao` (voto por seção), `eleitorado_local_votacao` (locais com endereço e coordenadas),
   `votacao_candidato_munzona`, `detalhe_votacao_munzona`, `perfil_eleitorado`, `consulta_cand` (candidatos),
   `bem_candidato`, prestação de contas (receitas e despesas).
2. IBGE — https://servicodados.ibge.gov.br/api/docs: localidades (municípios, regiões imediatas) e malhas (GeoJSON
   de municípios por UF, para o mapa). População e PIB municipal via SIDRA.
3. TSE divulgação ao vivo — https://resultados.tse.jus.br (já integrado).
Nada de Câmara, Senado ou Portal da Transparência nesta etapa.

## Fases e critérios de pronto
Trabalhe uma fase por vez. Ao fim de cada fase: testes passando, commit, e um resumo curto do que mudou.

**Fase 1 — VPS e dados reais (2024 e 2022)**
- `server/docker-compose.yml`, `server/etl/`, `server/api/`, `server/Caddyfile`, `server/install.sh` (um comando).
- ETL idempotente e retomável, ano a ano, baixando devagar com retentativa. Nunca contornar bloqueio do TSE.
- Tabelas no DuckDB: `voto_secao`, `local_votacao`, `municipio`, `candidato`, `detalhe_munzona`.
- Validação automática: total nacional do 2º turno 2022 tem que dar Lula 60.345.999 e Bolsonaro 58.206.354.
  Se não bater, a carga falha.
- Pronto quando: `GET /api/municipio/{cd}` responde em menos de 100 ms com todas as eleições da cidade.

**Fase 2 — Raio-X da cidade de verdade**
- `municipio.html` lê a API. Mostra: quem venceu cada eleição, força dos partidos no tempo, participação,
  e o mapa de locais de votação da cidade (pontos coloridos por vencedor, usando as coordenadas do TSE).
- Cidade × cidade: comparar com outra cidade ou com a média do estado.
- Pronto quando: página abre em menos de 1 s (Lighthouse mobile ≥ 90) e funciona em 390px.

**Fase 3 — Mapa do Brasil e dos estados**
- Malhas do IBGE simplificadas (TopoJSON), coloridas por vencedor ou por partido.
- Toque no município abre o Raio-X. Pronto quando o mapa de SP (645 municípios) desenha em menos de 1 s no celular.

**Fase 4 — Compartilhamento**
- Cada resultado gera imagem 1080×1350 (Instagram) e 1080×1080, com a fonte do TSE na imagem.
- Botão usa Web Share API com arquivo; sem suporte, baixa a imagem. Página com Open Graph por cidade.

**Fase 5 — App instalável**
- PWA: manifest, ícones, service worker com cache das páginas de cidade já vistas.

## Design
- Use os tokens de `assets/app.css` (paleta da urna: corpo cinza-esverdeado, teclas pretas, verde do CONFIRMA
  para ação e ao vivo, laranja do CORRIGE para alerta; vermelho/azul só para candidatos 13/22).
  Fontes: Bricolage Grotesque (títulos e números) e Instrument Sans (texto).
- Design comportamental: uma pergunta por tela ("Como sua cidade votou?"); resposta antes do detalhe;
  número grande com frase que interpreta ("Lula venceu aqui por 12 pontos"); favoritos sem cadastro;
  sem dark patterns (nada de contagem regressiva falsa, pop-up de saída, cadastro para ver dado público).
- Acessibilidade: contraste AA, foco visível, `prefers-reduced-motion`, leitores de tela nos gráficos.

## Como trabalhar
- Antes de codar cada fase, mostre o plano em até 10 linhas e espere meu ok.
- Não faça deploy na VPS por conta própria: gere os arquivos e me diga o comando exato para rodar.
- Se uma fonte do TSE ou do IBGE recusar acesso, pare e me avise; não tente contornar.
- Escreva testes para o ETL com amostras reais pequenas (poucas linhas de cada CSV, em `tests/fixtures/`).

Comece pela Fase 1.
