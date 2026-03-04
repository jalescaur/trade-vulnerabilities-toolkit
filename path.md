ai-infrastructure-trade/
├─ CITATION.cff
├─ README.md
├─ LICENSE
├─ environment.yml                 # ou requirements.txt (prefira conda se possível)
├─ .gitignore
├─ .gitattributes                  # opcional (ex.: linguist, line endings)

├─ data/
│  ├─ raw/                         # NÃO versionar (ou versionar só amostras)
│  │  ├─ README.md                 # explica fonte, período, como obter
│  │  └─ sample/                   # pequeno recorte versionado (ex.: 1 ano / 1 segmento)
│  ├─ external/                    # dicionários, tabelas auxiliares, ISO, etc.
│  └─ processed/                   # outputs intermediários (gerados), não versionar

├─ notebooks/
│  ├─ 00_setup_environment.ipynb
│  ├─ 01_ingest_comtrade.ipynb
│  ├─ 02_clean_normalize.ipynb
│  ├─ 03_metrics_concentration_dependency.ipynb
│  ├─ 04_figures_bw_publication.ipynb
│  └─ 99_sanity_checks_audit.ipynb

├─ src/
│  ├─ __init__.py
│  ├─ config.py                    # paths, constantes, anos, segmentos
│  ├─ io/
│  │  ├─ load.py                   # load_data_robust, readers
│  │  └─ validate.py               # audits (ISO, missing, duplicates)
│  ├─ taxonomy/
│  │  ├─ basket.py                 # ai_basket_meta + helpers
│  │  └─ regions.py                # region_map + get_region
│  ├─ metrics/
│  │  ├─ concentration.py          # HHI, CR3/CR5, entropy
│  │  ├─ dependency.py             # top1 share, exposure matrices
│  │  └─ shock.py                  # remove-top-supplier scenarios
│  ├─ viz/
│  │  ├─ style_bw.py               # set_bw_style + save_figure
│  │  └─ plots.py                  # funções de gráficos P&B
│  └─ utils/
│     ├─ logging.py
│     └─ helpers.py

├─ outputs/
│  ├─ tables/                      # versionável (CSV), gerado pelo pipeline
│  ├─ figures/                     # versionável (PDF/PNG 600dpi)
│  └─ logs/                        # não versionar (ou versionar só resumo)

├─ paper/
│  ├─ chapter.md                   # ou .tex (se você escrever em LaTeX)
│  ├─ references.bib
│  ├─ figs/                        # links/symlinks para outputs/figures (ou cópias)
│  └─ tables/                      # idem para outputs/tables

├─ scripts/
│  ├─ run_all.py                   # roda pipeline fim-a-fim (gera outputs)
│  └─ make_release.sh              # opcional (zip/DOI prep)

└─ tests/
   ├─ test_metrics.py              # mínimo: HHI/CR5, sanity checks
   └─ test_io.py