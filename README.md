# Relatório Executivo de Incidentes Zabbix

Projeto em Python para consultar incidentes do Zabbix, organizar os dados por
unidade escolar, equipamento, severidade e tempo offline, e gerar relatórios em
HTML interativo, PDF e Excel.

O objetivo é transformar dados técnicos do Zabbix em uma visão operacional mais
clara, útil para acompanhamento diário, análise de impacto e envio de
informações para supervisão.

## Visão Geral

Este projeto coleta incidentes diretamente da API do Zabbix e gera um relatório
executivo com foco nos chamados abertos. O HTML possui filtros, painéis de
indicadores, ranking de unidades, ranking de equipamentos, tipos de incidente,
tempo offline e janelas de detalhe por incidente.

Além do relatório geral, também é possível gerar relatórios específicos por
tipo de equipamento, como `Terminal Facial`, `Câmera`, `Mikrotik`, `Switch` e
outros.

## Principais Recursos

- Consulta de incidentes diretamente na API do Zabbix.
- Relatório histórico completo de incidentes abertos.
- Relatórios por período, como últimas 24 horas, 2 dias, 5 dias, 7 dias e 30 dias.
- Relatório por data inicial, usando `--desde`.
- Relatório específico por tipo de equipamento.
- Separação de incidentes de unidades escolares.
- Separação própria para o Servidor Zabbix.
- Separação própria para equipamentos da CONFEA VPN.
- Classificação automática de equipamentos.
- Classificação consolidada dos tipos de incidente.
- Indicadores de severidade, prioridade e tempo offline.
- HTML interativo com filtros, busca, ordenação e exportação CSV.
- Geração de PDF executivo.
- Geração de planilha Excel com dados estruturados.
- Template HTML separado em estrutura, CSS e JavaScript para facilitar manutenção.

## Tecnologias Utilizadas

- Python
- Zabbix API JSON-RPC
- Pandas
- OpenPyXL
- Jinja2
- Python Dotenv
- HTML
- CSS
- JavaScript

## Estrutura do Projeto

```text
.
├── README.md
├── COMANDOS.md
├── documentacao/
│   └── Guia_Operacional_Zabbix.pdf
├── entrega_supervisor/
│   ├── Relatorio_Executivo_Incidentes_Zabbix_Atual.pdf
│   ├── Relatorio_Executivo_Incidentes_Zabbix_Dados.xlsx
│   ├── Relatorio_Executivo_Incidentes_Zabbix_Interativo.html
│   └── Relatorio_Executivo_Incidentes_Zabbix_Atual.zip
└── zabbix-report/
    ├── .env.example
    ├── .gitignore
    ├── classifiers.py
    ├── gerar_documentacao_pdf.py
    ├── pdf_report.py
    ├── requirements.txt
    ├── summary.py
    ├── test_zabbix_api.py
    ├── zabbix_api.py
    ├── zabbix_report.py
    └── templates/
        ├── report_template.html
        ├── report_styles.css
        └── report_script.js
```

## Arquivos Principais

| Arquivo | Função |
| --- | --- |
| `zabbix-report/zabbix_report.py` | Script principal. Coordena a coleta, tratamento e geração dos relatórios. |
| `zabbix-report/zabbix_api.py` | Cliente de comunicação com a API do Zabbix. |
| `zabbix-report/classifiers.py` | Regras de classificação de equipamento, unidade e tipo de incidente. |
| `zabbix-report/summary.py` | Cálculo dos indicadores e rankings do relatório. |
| `zabbix-report/pdf_report.py` | Geração do relatório em PDF. |
| `zabbix-report/test_zabbix_api.py` | Teste rápido de conexão com a API do Zabbix. |
| `zabbix-report/templates/report_template.html` | Estrutura HTML/Jinja do relatório. |
| `zabbix-report/templates/report_styles.css` | Estilos visuais do relatório HTML. |
| `zabbix-report/templates/report_script.js` | Filtros, ordenação, modais e exportação CSV do HTML. |
| `COMANDOS.md` | Guia rápido com os comandos usados no dia a dia. |

## Requisitos

- Python 3.7 ou superior.
- Acesso à API do Zabbix.
- Token de API válido no Zabbix.
- Dependências listadas em `zabbix-report/requirements.txt`.

## Configuração Inicial

Entre na pasta do projeto:

```bash
cd /mnt/c/Users/chip/Documents/relat.incidentes.zabbix
```

Crie o arquivo `.env` a partir do exemplo:

```bash
cp zabbix-report/.env.example zabbix-report/.env
```

Edite o arquivo `zabbix-report/.env` com as informações reais do seu Zabbix:

```env
ZABBIX_URL=https://seu-zabbix.example.com/api_jsonrpc.php
ZABBIX_TOKEN=cole_seu_token_do_zabbix_aqui
```

O arquivo `.env` real não deve ser enviado ao GitHub, pois contém credenciais.

## Instalação

Crie o ambiente virtual, caso ainda não exista:

```bash
python3 -m venv zabbix-report/venv
```

Ative o ambiente virtual:

```bash
source zabbix-report/venv/bin/activate
```

Instale as dependências:

```bash
pip install -r zabbix-report/requirements.txt
```

## Testar Conexão com o Zabbix

Antes de gerar relatórios, valide se a conexão com a API está funcionando:

```bash
python zabbix-report/test_zabbix_api.py
```

Esse teste ajuda a confirmar se:

- O arquivo `.env` foi encontrado.
- A URL da API está correta.
- O token está válido.
- O Zabbix está respondendo.

## Gerar Relatório Principal

Este é o comando mais usado no projeto:

```bash
python zabbix-report/zabbix_report.py --periodo historico --status abertos
```

Esse comando:

- Busca o histórico completo de incidentes ainda abertos.
- Ignora incidentes resolvidos.
- Separa incidentes de unidades escolares.
- Separa eventos do Servidor Zabbix.
- Separa eventos da CONFEA VPN.
- Gera HTML, PDF e Excel.

Os arquivos são criados em:

```text
zabbix-report/reports/
```

## Gerar Relatório por Período

Últimas 24 horas:

```bash
python zabbix-report/zabbix_report.py --periodo 24h --status abertos
```

Últimos 2 dias:

```bash
python zabbix-report/zabbix_report.py --periodo 2d --status abertos
```

Últimos 7 dias:

```bash
python zabbix-report/zabbix_report.py --periodo 7d --status abertos
```

Últimos 30 dias:

```bash
python zabbix-report/zabbix_report.py --periodo 30d --status abertos
```

## Gerar Relatório Desde uma Data

Use o formato `AAAA-MM-DD`:

```bash
python zabbix-report/zabbix_report.py --desde 2026-06-01 --status abertos
```

Esse modo é útil quando o histórico completo estiver pesado ou quando for
necessário analisar um intervalo específico.

## Gerar Relatório por Equipamento

Exemplo para `Terminal Facial`:

```bash
python zabbix-report/zabbix_report.py --periodo historico --status abertos --equipamento "Terminal Facial"
```

Exemplo para `Câmera`:

```bash
python zabbix-report/zabbix_report.py --periodo historico --status abertos --equipamento "Câmera"
```

Exemplo para `Mikrotik`:

```bash
python zabbix-report/zabbix_report.py --periodo historico --status abertos --equipamento "Mikrotik"
```

O relatório por equipamento não quebra o relatório principal. Ele gera arquivos
separados com o nome do equipamento no nome do arquivo.

## Saídas Geradas

Para cada execução, o projeto gera:

```text
report_AAAA-MM-DD_periodo.xlsx
report_AAAA-MM-DD_periodo.html
report_AAAA-MM-DD_periodo.pdf
```

Cada formato tem uma finalidade:

- `.html`: relatório interativo para análise, busca e filtros.
- `.pdf`: relatório formal para envio e apresentação.
- `.xlsx`: planilha para análise detalhada dos dados.

## O Que Existe no HTML

O relatório HTML possui:

- Resumo executivo.
- Indicadores de incidentes abertos.
- Métricas de tempo offline.
- Distribuição por severidade.
- Ranking de equipamentos mais afetados.
- Ranking de tipos de incidente.
- Ranking de hosts com mais incidentes.
- Ranking de unidades mais afetadas.
- Filtro por unidade escolar.
- Filtro por equipamento.
- Filtro por severidade.
- Filtro por tempo offline.
- Busca geral.
- Ordenação de colunas.
- Janela de detalhes por incidente.
- Exportação CSV dos dados filtrados.
- Janela separada para Servidor Zabbix.
- Janela separada para CONFEA VPN.

## Classificação de Equipamentos

A classificação de equipamentos fica em:

```text
zabbix-report/classifiers.py
```

A ordem operacional usada no relatório é:

1. Mikrotik
2. Switch
3. NVR
4. Central de Alarme
5. Terminal Facial
6. Portal Detector de Metal
7. Câmera
8. Servidor Zabbix
9. Servidor
10. Outros

Essa ordem ajuda a manter o filtro do HTML previsível e organizado.

## Tipos de Incidente

O projeto consolida textos técnicos do Zabbix em famílias de incidente, evitando
que pequenas variações gerem várias categorias diferentes.

Exemplos:

- `Unavailable by ICMP ping`
- `High ICMP ping response time`
- `High ICMP ping loss`
- `No SNMP data collection`
- `Interface down`
- `Ethernet lower speed`
- `Temperature above threshold`
- `High bandwidth usage`

As regras ficam na função:

```python
classify_incident_type(incident)
```

Arquivo:

```text
zabbix-report/classifiers.py
```

## Unidades Escolares

O relatório usa as informações vindas do Zabbix para identificar unidades
escolares. A organização considera o código da unidade, como `1011`, `1012`,
`1091`, entre outros.

Quando o host pertence a uma unidade escolar, ele entra no relatório principal.
Quando o host é o `0000-SRV Zabbix server`, ele fica separado em uma janela
própria do Servidor Zabbix.

## Servidor Zabbix e CONFEA VPN

O projeto trata alguns grupos de forma separada:

- `Servidor Zabbix`: eventos do próprio servidor de monitoramento.
- `CONFEA VPN`: servidores monitorados por ping através de VPN.

Essa separação evita misturar eventos internos ou externos com incidentes das
unidades escolares.

## Segurança

Cuidados obrigatórios:

- Nunca envie o arquivo `.env` real para o GitHub.
- Nunca coloque token, senha ou credencial no código.
- Use `.env.example` apenas com valores fictícios.
- Gere tokens com permissões mínimas necessárias.
- Revogue tokens antigos caso eles sejam expostos.
- Não compartilhe relatórios com dados sensíveis sem validação.

## Arquivos Ignorados pelo Git

Devem ficar fora do repositório:

- `.env`
- `venv/`
- `reports/`
- caches do Python
- arquivos temporários
- credenciais locais

Isso mantém o repositório mais leve e seguro.

## Fluxo Recomendado de Uso

1. Entrar na pasta do projeto.
2. Ativar a `venv`.
3. Testar a conexão, se necessário.
4. Gerar o relatório desejado.
5. Abrir o HTML em `zabbix-report/reports/`.
6. Conferir filtros, rankings e detalhes.
7. Enviar PDF, HTML ou Excel conforme a necessidade.

Comandos mais comuns:

```bash
cd /mnt/c/Users/chip/Documents/relat.incidentes.zabbix
source zabbix-report/venv/bin/activate
python zabbix-report/zabbix_report.py --periodo historico --status abertos
```

## Manutenção do Projeto

Ao adicionar ou ajustar regras:

- Use `classifiers.py` para novas classificações.
- Use `summary.py` para novos indicadores.
- Use `report_styles.css` para ajustes visuais.
- Use `report_script.js` para filtros e interações do HTML.
- Use `pdf_report.py` para melhorias no PDF.

Evite colocar toda a lógica em `zabbix_report.py`. Esse arquivo deve continuar
funcionando como coordenador do fluxo.

## Roadmap

Melhorias previstas:

- Aprimorar o PDF executivo.
- Adicionar gráficos no HTML.
- Melhorar o README continuamente.
- Adicionar screenshots do relatório.
- Adicionar testes automatizados.
- Melhorar performance do HTML para grandes volumes.
- Criar rotina de geração agendada.
- Criar uma versão executável futuramente.
- Revisar periodicamente segurança de tokens e credenciais.

## Observação Importante

O arquivo `zabbix-report/templates/report_template.html` é um template Jinja.
Ele não deve ser aberto diretamente como relatório final.

O relatório final fica em:

```text
zabbix-report/reports/
```

Abra sempre o arquivo `.html` gerado dentro da pasta `reports/`.

## Status do Projeto

O projeto já gera relatórios funcionais em HTML, PDF e Excel, com filtros
interativos e separação operacional dos principais grupos de incidentes.

Ele segue em evolução contínua, com foco em clareza, confiabilidade e utilidade
para acompanhamento técnico e executivo.
