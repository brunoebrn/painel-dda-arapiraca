# Painel Epidemiológico — Doença Diarreica Aguda (CID A09)
### Secretaria Municipal de Saúde de Arapiraca — 2025

[![GitHub Pages](https://img.shields.io/badge/Acesso%20p%C3%BAblico-GitHub%20Pages-blue?style=flat-square)](https://brunoebrn.github.io/painel-dda-arapiraca/)

Painel interativo de vigilância epidemiológica para monitoramento dos atendimentos por Doença Diarreica Aguda (DDA) no município de Arapiraca/AL, com dados do ano de 2025 extraídos do sistema e-SUS APS.

---

## Acesso

🔗 **[brunoebrn.github.io/painel-dda-arapiraca](https://brunoebrn.github.io/painel-dda-arapiraca/)**

O painel é um arquivo HTML único, autocontido e funciona sem conexão com a internet após carregado.

---

## Funcionalidades

- **Visão Geral** — Cards de resumo (atendimentos totais, pacientes únicos, menores de 5 anos), série temporal mensal e distribuição por faixa etária
- **Análise Territorial** — Tabelas por UBS, bairro, equipe de saúde e microárea, com ordenação interativa
- **Perfil Epidemiológico** — Pirâmide etária, distribuição por sexo, CIDs mais frequentes, recorrência de atendimentos e análise de Demanda Espontânea (Complexo)
- **Mapa Territorial** — Choropleth interativo (Leaflet.js) com taxa de incidência por bairro, baseado em polígonos GeoJSON dos 41 bairros de Arapiraca
- **Filtros avançados** — Zona, UBS, bairro, faixa etária, sexo e mês
- **Toggles globais** — `< 5 anos`, `↺ Casos Repetidos`, `🏥 Demanda Espontânea`

---

## Fonte dos Dados

| Fonte | Conteúdo |
|---|---|
| e-SUS APS — Ficha de Atendimento Individual | Atendimentos ambulatoriais por CID A09 |
| IBGE — Malha de Bairros Arapiraca | Polígonos GeoJSON para o mapa |

**Período:** Janeiro a Dezembro de 2025
**Registros processados:** 5.388 atendimentos
**Proteção de dados:** Agregações com n < 5 suprimidas conforme LGPD (Lei 13.709/2018). Nenhum dado individual é armazenado ou publicado.

---

## Estrutura do Repositório

```
painel-dda-arapiraca/
├── index.html              # Painel completo (autocontido, ~929 KB)
├── build_dashboard2.py     # Gerador do painel (Python)
├── build_data_v3.py        # Pipeline de dados (Python)
├── dashboard_data_v3.json  # Dados agregados pré-processados
├── arapiraca_bairros.json  # GeoJSON dos bairros de Arapiraca
└── .gitignore              # Exclui arquivos brutos com dados de pacientes
```

> ⚠️ Os arquivos `.xlsx` originais exportados do e-SUS **não são versionados** por conterem identificadores de pacientes. Eles devem ser mantidos localmente e nunca publicados.

---

## Como Atualizar o Painel

### Pré-requisitos

```bash
pip install pandas openpyxl
```

### Passo a passo

**1. Exportar os dados do e-SUS APS**

No e-SUS, exporte as fichas de atendimento individual para o período desejado em `.xlsx` e coloque na pasta do projeto.

**2. Rodar o pipeline de dados**

```bash
python build_data_v3.py
```

Gera o arquivo `dashboard_data_v3.json` com todos os dados agregados (sem identificadores individuais).

**3. Gerar o painel**

```bash
python build_dashboard2.py
```

Gera o `index.html` atualizado com os novos dados embutidos.

**4. Publicar**

```bash
git add index.html dashboard_data_v3.json
git commit -m "Atualização dos dados — <período>"
git push
```

O GitHub Pages publica automaticamente em 1–2 minutos.

---

## Tecnologias

| Biblioteca | Versão | Uso |
|---|---|---|
| [Chart.js](https://www.chartjs.org/) | 4.4.0 | Gráficos (embutido) |
| [Leaflet.js](https://leafletjs.com/) | 1.9.4 | Mapa interativo (embutido) |
| Python / Pandas | — | Pipeline de dados |

---

## Autor

**Dr. Bruno Eduardo Bastos Rolim Nunes**
CRM 10.089/AL — Médico de Família e Comunidade
Secretaria Municipal de Saúde de Arapiraca — Vigilância em Saúde
Professor — IESC 5 / UFAL Campus Arapiraca

---

*Dados anonimizados conforme LGPD (Lei 13.709/2018). Agregações com n < 5 suprimidas.*
