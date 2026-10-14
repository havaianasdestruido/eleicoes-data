# Test Notebooks - Eleições 2026

Esta pasta contém **6 Jupyter Notebooks** interativos para explorar os dados de snapshots do TSE.

## 📚 Notebooks

1. **01_overview.ipynb** - Visão geral: lista snapshots, metadados, ranking, estatísticas gerais com gráficos de pizza
2. **02_vote_distribution.ipynb** - Distribuição de votos: barras horizontais, pizza share, tipos de voto, por partido, top2
3. **03_time_series.ipynb** - Evolução temporal: seções apuradas, votos ao longo do tempo, margem entre líderes, heatmap estabilidade
4. **04_turnout_analysis.ipynb** - Comparecimento: participação, abstenção, brancos/nulos, média por seção, séries temporais
5. **05_candidate_comparison.ipynb** - Comparativo candidatos: 2º turno, coligações, simulação de virada, métricas normalizadas
6. **06_data_explorer.ipynb** - Explorer interativo: funções utilitárias, comparação snapshots, filtros, export CSV, validação, dashboard resumo

## 🖼️ Imagens Embutidas

Todos os notebooks foram **executados** e possuem:
- Gráficos matplotlib/seaborn embutidos como PNG base64 no `.ipynb` (não são limpos após execução)
- Imagens PNG também salvas externamente no diretório para uso em relatórios
- Tabelas pandas renderizadas

Arquivos PNG gerados:
- overview_stats.png
- vote_distribution_bar.png, vote_distribution_pie.png, vote_types.png, vote_by_party.png, top2_comparison.png
- timeseries_sections.png, timeseries_all_candidates.png, timeseries_top4_pct.png, timeseries_margin.png, timeseries_stability.png
- turnout_analysis.png, turnout_timeseries.png, protest_votes.png, avg_per_section.png
- candidate_top2_vs_others.png, candidate_normalized.png, coalition_votes.png, votes_needed_to_tie.png
- explorer_delta.png, dashboard_resumo.png

## 🚀 Como usar

```bash
pip install pandas matplotlib seaborn jupyter
jupyter notebook test/
# ou
jupyter lab test/
```

Os notebooks detectam automaticamente o diretório `data/` relativo:
- `../data` (quando em test/)
- `data` (quando na raiz)
- `/home/user/eleicoes-data/data` (fallback absoluto)

## 📊 Dados

- Fonte: TSE - Tribunal Superior Eleitoral
- Eleição 6257, Cargo Presidente, abrangência BR
- 43 snapshots de 2026-10-05 a 2026-10-14
- Formato: `data/presidente_br_YYYYmmdd_HHMMSSZ.json` com metadata + payload completo

## ✅ Não limpar outputs

Conforme solicitado, os notebooks **não têm seus outputs limpos** após execução de testes. As imagens permanecem embutidas no JSON do `.ipynb`.

## 🧪 Testes

Os testes originais em `tests/test_scrape_tse.py` continuam funcionando. Os notebooks são complementares e não interferem.
