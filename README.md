# Relatório Executivo de Incidentes Zabbix

Projeto em Python para consultar incidentes do Zabbix, organizar os dados de
monitoramento e gerar relatórios executivos em HTML, Excel e PDF.

O objetivo é transformar informações técnicas da API do Zabbix em uma visão
mais clara, interativa e útil para análise operacional, acompanhamento de
incidentes abertos e apresentação para supervisão.

> Projeto em desenvolvimento contínuo.

## Visão Geral

O projeto coleta incidentes diretamente da API JSON-RPC do Zabbix, processa os
dados e gera um relatório focado em incidentes abertos.

O relatório permite analisar:

- quantidade de incidentes abertos;
- severidade dos incidentes;
- tempo offline;
- equipamentos mais afetados;
- tipos de incidente mais recorrentes;
- hosts com mais ocorrências;
- unidades escolares mais afetadas;
- eventos separados do Servidor Zabbix;
- eventos separados da CONFEA VPN.

Além do relatório geral, também é possível gerar relatórios filtrados por tipo
de equipamento, como `Terminal Facial`, `Câmera`, `Mikrotik`, `Switch`, `NVR`,
`Central de Alarme` e `Portal Detector de Metal`.

## Principais Recursos

- Consulta de incidentes diretamente na API do Zabbix.
- Relatório histórico completo de incidentes abertos.
- Relatórios por período, como 24 horas, 2 dias, 5 dias, 7 dias e 30 dias.
- Relatório a partir de uma data específica com `--desde`.
- Relatório por tipo de equipamento com `--equipamento`.
- Classificação automática de equipamentos.
- Consolidação de tipos de incidente.
- Cálculo de indicadores executivos.
- Gráficos visuais no HTML.
- Ranking por severidade, equipamento, host, unidade e tipo de incidente.
- Filtro por unidade escolar, equipamento, severidade e tempo offline.
- Busca geral por host, incidente, equipamento ou severidade.
- Ordenação de colunas.
- Janela de detalhes por incidente.
- Link de abertura do incidente diretamente no Zabbix.
- Exportação CSV dos dados filtrados no HTML.
- Geração de planilha Excel.
- Geração de PDF executivo.
- Separação entre HTML, CSS e JavaScript para facilitar manutenção.
- Uso de `.env` para proteger credenciais.
- Verificação local de possíveis segredos antes de publicar.
- Workflow no GitHub Actions para validação automática.

## Tecnologias Utilizadas

- Python
- Zabbix API JSON-RPC
- Pandas
- OpenPyXL
- Jinja2
- python-dotenv
- HTML
- CSS
- JavaScript
- Git
- GitHub
- GitHub Actions

## Estrutura do Projeto

```text
.
├── README.md
├── CHANGELOG.md
├── COMANDOS.md
├── GUIA_RAPIDO_RELATORIO_POR_EQUIPAMENTO.md
├── SEGURANCA.md
├── ABRIR_RELATORIO_POR_EQUIPAMENTO.bat
├── gerar_relatorio_equipamento.bat
├── gerar_relatorio_equipamento.sh
├── documentacao/
│   └── Guia_Operacional_Zabbix.pdf
├── scripts/
│   └── check_secrets.py
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
    ├── reports/
    └── templates/
        ├── report_template.html
        ├── report_styles.css
        └── report_script.js
```

## Arquivos Principais

| Arquivo | Função |
| --- | --- |
| `zabbix-report/zabbix_report.py` | Script principal. Coordena coleta, tratamento e geração dos relatórios. |
| `zabbix-report/zabbix_api.py` | Cliente responsável pela comunicação com a API do Zabbix. |
| `zabbix-report/observability.py` | Tempos, métricas seguras, gargalos e diagnóstico opcional da execução. |
| `zabbix-report/classifiers.py` | Regras de classificação de unidade, equipamento e tipo de incidente. |
| `zabbix-report/summary.py` | Cálculo dos indicadores, rankings e resumos do relatório. |
| `zabbix-report/pdf_report.py` | Geração do relatório executivo em PDF. |
| `zabbix-report/test_zabbix_api.py` | Teste rápido de conexão com a API do Zabbix. |
| `zabbix-report/templates/report_template.html` | Estrutura HTML/Jinja do relatório. |
| `zabbix-report/templates/report_styles.css` | Estilos visuais do relatório HTML. |
| `zabbix-report/templates/report_script.js` | Filtros, busca, ordenação, modais e exportação CSV. |
| `scripts/benchmark_exports.py` | Benchmark reproduzível das exportações com dados fictícios. |
| `BENCHMARK_SPRINT_5.md` | Método, resultados e limitações da otimização orientada por evidências. |
| `scripts/check_secrets.py` | Verificação local de possíveis tokens, senhas e segredos. |
| `COMANDOS.md` | Guia prático com comandos usados no dia a dia. |
| `CHANGELOG.md` | Histórico das principais evoluções do projeto. |

## Requisitos

- Python 3.7 ou superior.
- Acesso à API do Zabbix.
- Token válido da API do Zabbix.
- Dependências listadas em `zabbix-report/requirements.txt`.

## Configuração Inicial

Entre na pasta do projeto:

```bash
cd /mnt/c/Users/chip/Desktop/lcmrcsWorkspace/relat.incidentes.zabbix
```

Crie o arquivo `.env` a partir do exemplo:

```bash
cp zabbix-report/.env.example zabbix-report/.env
```

Edite o arquivo `zabbix-report/.env` com as informações reais do seu ambiente:

```env
ZABBIX_URL=https://seu-zabbix.example.com/api_jsonrpc.php
ZABBIX_TOKEN=cole_seu_token_do_zabbix_aqui
```

O arquivo `.env` real não deve ser enviado ao GitHub, pois contém credenciais.

## Instalação

Crie o ambiente virtual:

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

Antes de gerar relatórios, valide a conexão com a API:

```bash
python zabbix-report/test_zabbix_api.py
```

Esse teste confirma se:

- o arquivo `.env` foi encontrado;
- a URL da API está correta;
- o token está válido;
- o Zabbix está respondendo.

## Tela Inicial para Gerar Relatórios

O caminho mais simples para gerar relatórios é abrir a tela local do projeto.
Ela permite escolher período, situação, equipamento e quantidade de relatórios
mantidos sem memorizar comandos.

No Windows:

```text
abrir_tela_relatorio.bat
```

No Linux ou WSL:

```bash
./abrir_tela_relatorio.sh
```

A tela abre no navegador em:

```text
http://127.0.0.1:8765/
```

Pela tela, é possível:

- gerar relatório histórico, 24h, 2 dias, 5 dias, 7 dias, 15 dias ou 30 dias;
- filtrar por equipamento;
- filtrar por código ou nome de unidade escolar;
- escolher incidentes abertos, resolvidos ou todos;
- manter apenas o relatório mais recente ou preservar mais execuções;
- abrir diretamente o HTML, Excel e PDF gerados.

## Gerar Relatório Principal pelo Terminal

Comando mais usado no projeto:

```bash
python zabbix-report/zabbix_report.py --periodo historico --status abertos
```

Esse comando:

- busca o histórico completo de incidentes ainda abertos;
- ignora incidentes resolvidos;
- separa incidentes de unidades escolares;
- separa eventos do Servidor Zabbix;
- separa eventos da CONFEA VPN;
- gera HTML, PDF e Excel.

Os arquivos são criados em:

```text
zabbix-report/reports/
```

Por padrão, o script mantém apenas o conjunto mais recente de relatórios nessa
pasta. Isso evita acúmulo de arquivos antigos ou desatualizados.

Para manter mais execuções, use:

```bash
python zabbix-report/zabbix_report.py --periodo historico --status abertos --manter-relatorios 3
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

O relatório por equipamento não altera o relatório principal. Ele gera arquivos
separados com o nome do equipamento no nome do arquivo.

## Atalhos de Execução

O projeto possui atalhos para facilitar o uso por pessoas que não querem lidar
diretamente com comandos Python.

No Windows:

```text
ABRIR_RELATORIO_POR_EQUIPAMENTO.bat
```

No Linux ou WSL:

```bash
./gerar_relatorio_equipamento.sh
```

O atalho do Windows pode:

- verificar se o `.env` existe;
- criar a configuração inicial;
- criar a `venv`, se necessário;
- instalar dependências;
- perguntar qual equipamento será filtrado;
- gerar o relatório;
- abrir o HTML mais recente.

Também existe um guia específico para esse fluxo:

```text
GUIA_RAPIDO_RELATORIO_POR_EQUIPAMENTO.md
```

## Saídas Geradas

Para cada execução, o projeto gera arquivos semelhantes a:

```text
report_AAAA-MM-DD_periodo.html
report_AAAA-MM-DD_periodo.pdf
report_AAAA-MM-DD_periodo.xlsx
```

Finalidade de cada formato:

- `.html`: relatório interativo para análise, filtros e busca.
- `.pdf`: versão executiva compacta para apresentação e envio.
- `.xlsx`: planilha para análise detalhada dos dados.

O PDF principal resume os indicadores canônicos, prioridades, recorrências e
criticidade, sem repetir todos os eventos. Para gerar também o detalhamento
técnico em arquivo separado:

```bash
python zabbix-report/zabbix_report.py --periodo 7d --pdf-detalhado
```

O arquivo adicional segue o padrão:

```text
report_AAAA-MM-DD_periodo_anexo_tecnico.pdf
```

Como a pasta `reports/` é uma área de saída gerada automaticamente, relatórios
antigos são removidos conforme a política definida por `--manter-relatorios`.

## O Que Existe no HTML

O relatório HTML contém:

- cabeçalho executivo;
- indicadores principais;
- gráficos de severidade, equipamento e tempo offline;
- ranking de equipamentos mais afetados;
- ranking de tipos de incidente;
- ranking de hosts com mais incidentes;
- ranking de unidades mais afetadas;
- filtro por unidade escolar;
- filtro por equipamento;
- filtro por severidade;
- filtro por tempo offline;
- busca geral;
- ordenação por colunas;
- janela de detalhes por incidente;
- exportação CSV dos dados filtrados;
- janela separada para Servidor Zabbix;
- janela separada para CONFEA VPN.

A tabela operacional materializa 50, 100 ou 250 linhas por página para manter
a navegação leve em grandes volumes. Busca, filtros, contadores, ordenação,
modais e CSV continuam considerando o conjunto completo de incidentes.

Relatórios com mais de 5.000 linhas filtradas não são expandidos para impressão
direta, evitando travamentos do navegador. O CSV permanece disponível com todo
o resultado filtrado.

## Validação em Navegador

A suíte da Sprint 6 abre relatórios locais com dados fictícios no Edge ou
Chrome do Windows, sem acessar o Zabbix:

```bash
python scripts/validate_html_browser.py
```

Ela cobre 0, 10, 7.171 e 20.000 registros, repete o cenário de 7.171 três
vezes, testa as interações essenciais e grava os resultados em
`VALIDACAO_NAVEGADOR_SPRINT_6.json` e `VALIDACAO_NAVEGADOR_SPRINT_6.md`.
Essa validação é destinada ao desenvolvimento e não adiciona dependências ao
fluxo normal de geração.

## Classificação de Equipamentos

A classificação de equipamentos fica em:

```text
zabbix-report/classifiers.py
```

Ordem operacional usada no relatório:

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

Essa ordem mantém filtros, rankings e telas de análise mais previsíveis.

## Tipos de Incidente

O projeto consolida textos técnicos do Zabbix em famílias de incidente. Isso
evita que pequenas variações criem categorias duplicadas.

Exemplos de famílias:

- `Unavailable by ICMP ping`
- `High ICMP ping response time`
- `High ICMP ping loss`
- `No SNMP data collection`
- `Interface down`
- `Ethernet lower speed`
- `Temperature above threshold`
- `High bandwidth usage`

A regra principal fica em:

```python
classify_incident_type(incident)
```

Arquivo:

```text
zabbix-report/classifiers.py
```

## Unidades Escolares, Servidor Zabbix e CONFEA VPN

O relatório organiza os incidentes em grupos diferentes para evitar mistura de
contextos operacionais.

- `Unidades escolares`: incidentes dos equipamentos associados às unidades.
- `Servidor Zabbix`: eventos técnicos do próprio servidor de monitoramento.
- `CONFEA VPN`: servidores monitorados por ping através de VPN.

Essa separação deixa a análise mais fiel, porque eventos internos ou externos
não são misturados com incidentes das unidades escolares.

## Segurança

Cuidados obrigatórios:

- Nunca envie o arquivo `.env` real para o GitHub.
- Nunca coloque token, senha ou credencial no código.
- Use `.env.example` apenas com valores fictícios.
- Gere tokens com permissões mínimas necessárias.
- Revogue tokens antigos caso eles sejam expostos.
- Não compartilhe relatórios com dados sensíveis sem validação.
- Para imagens públicas, use dados fictícios ou sanitizados.

Antes de fazer commit ou publicar o projeto, rode:

```bash
python scripts/check_secrets.py
```

Também existe um guia dedicado:

```text
SEGURANCA.md
```

## Arquivos Ignorados pelo Git

Devem ficar fora do repositório:

- `.env`
- `venv/`
- `reports/`
- caches do Python;
- arquivos temporários;
- credenciais locais;
- entregas locais com dados sensíveis.

Isso mantém o repositório mais leve e seguro.

## Fluxo Recomendado de Uso

1. Entrar na pasta do projeto.
2. Ativar a `venv`.
3. Testar a conexão com o Zabbix, se necessário.
4. Gerar o relatório desejado.
5. Abrir o HTML em `zabbix-report/reports/`.
6. Conferir filtros, rankings e detalhes.
7. Enviar PDF, HTML ou Excel conforme a necessidade.

Comandos mais comuns:

```bash
cd /mnt/c/Users/chip/Desktop/lcmrcsWorkspace/relat.incidentes.zabbix
source zabbix-report/venv/bin/activate
python zabbix-report/zabbix_report.py --periodo historico --status abertos
```

## Manutenção do Projeto

### Conceitos dos indicadores

- **Evento**: cada ocorrência retornada pela API do Zabbix.
- **Incidente único**: agrupamento lógico por unidade, host, equipamento e tipo
  de incidente. A chave é normalizada, determinística e não depende da
  severidade nem de textos variáveis como o IP no nome do evento.
- **Recorrência**: repetição da mesma condição no período consultado.
- **Duração total**: da abertura até a geração para eventos abertos, ou da
  abertura até a resolução para eventos resolvidos.
- **Idade do passivo aberto**: tempo decorrido somente para eventos ainda
  abertos. Mais antigo, média e faixas de envelhecimento ignoram resolvidos.

Os testes automatizados usam somente dados fictícios e não acessam o Zabbix.

### Integridade e duração histórica

Antes de construir os incidentes, a coleta valida identificadores, timestamps,
recuperações, hosts, unidades, equipamentos e severidades. Dados recuperáveis
são normalizados com aviso; duplicatas e registros sem rastreabilidade ou tempo
confiável são descartados sem interromper os demais registros.

O mesmo resumo de integridade alimenta o selo e modal do HTML, a aba
`Integridade dos Dados` do Excel e o resumo compacto do PDF. Os avisos mostram
somente categorias e quantidades, nunca payloads, tokens, URLs ou endereços.

A duração histórica dos resolvidos permanece disponível nos dados canônicos e
nas exportações adequadas, sempre separada da idade do passivo aberto.

### Estratégia do PDF

O projeto mantém um gerador PDF nativo e sem serviços externos. Essa abordagem
foi preservada por oferecer o melhor equilíbrio atual entre portabilidade no
Windows/WSL, estabilidade e manutenção, sem exigir navegador ou motor de
conversão HTML. O PDF executivo usa apenas campos já consolidados por
`summary.py`; o anexo técnico recebe a lista de eventos sem recalcular
indicadores.

Seções executivas sem conteúdo são omitidas, os rankings têm limites fixos e o
número de páginas do documento principal não cresce com o volume de eventos.
HTML e Excel continuam sendo as fontes de detalhamento interativo e tabular.

### Observabilidade da geração

Toda execução apresenta no terminal um resumo compacto com tempo total, coleta
da API, processamento, exportações, registros, tamanhos, etapa mais demorada e
avisos. As medições usam `time.perf_counter()` e não alteram os indicadores ou
arquivos gerados.

Para persistir as métricas técnicas ao lado dos relatórios:

```bash
python zabbix-report/zabbix_report.py --periodo 7d --diagnostico
```

O arquivo `report_..._diagnostico.json` inclui somente período solicitado,
horários, durações, contagens, métodos da API, tamanhos, páginas, gargalo e
avisos. Tokens, URLs, IPs, payloads, hosts e conteúdo dos incidentes não são
armazenados. Sem `--diagnostico`, nenhum JSON é criado.

Ao adicionar ou ajustar regras:

- use `classifiers.py` para novas classificações;
- use `summary.py` para novos indicadores;
- use `report_styles.css` para ajustes visuais;
- use `report_script.js` para filtros e interações do HTML;
- use `pdf_report.py` para melhorias no PDF;
- use `observability.py` para métricas e limites de desempenho;
- mantenha `zabbix_report.py` como coordenador do fluxo principal.

Evite concentrar toda a lógica em um único arquivo. A separação atual facilita
manutenção, testes e evolução do projeto.

## GitHub Actions

O repositório possui workflow de validação automática. Ele ajuda a identificar
problemas básicos antes que alterações sejam consolidadas no GitHub.

Esse workflow não substitui testes completos, mas funciona como uma camada de
segurança para manter o projeto organizado.

## Roadmap

Melhorias previstas:

- Adicionar testes automatizados mais completos.
- Melhorar performance do HTML para grandes volumes.
- Criar rotina de geração agendada.
- Criar uma versão executável futuramente.
- Melhorar a experiência de instalação para outros usuários.
- Revisar periodicamente segurança de tokens e credenciais.
- Criar mais exemplos públicos com dados fictícios e sanitizados.

## Observação Importante

O arquivo `zabbix-report/templates/report_template.html` é um template Jinja.
Ele não deve ser aberto diretamente como relatório final.

O relatório final fica em:

```text
zabbix-report/reports/
```

Abra sempre o arquivo `.html` gerado dentro da pasta `reports/`.

## Status do Projeto

O projeto já gera relatórios funcionais em HTML, PDF e Excel, com filtros,
gráficos, rankings e separação operacional dos principais grupos de incidentes.

Ele segue em evolução contínua, com foco em clareza, confiabilidade, segurança
e utilidade para acompanhamento técnico e executivo.
