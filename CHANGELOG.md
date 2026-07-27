# Changelog

Histórico das principais evoluções do projeto **Relatório Executivo de Incidentes Zabbix**.

Este arquivo registra mudanças relevantes de forma simples, para facilitar acompanhamento técnico, prestação de contas e evolução do projeto.

## Em Desenvolvimento

### Adicionado

- Validação funcional em Microsoft Edge real com massas fictícias de 0, 10,
  7.171 e 20.000 registros, métricas por mediana, captura de console e prova de
  impressão PDF nativa.
- Script `scripts/validate_html_browser.py` para testar tema persistente, busca,
  filtros combinados, ordenação, paginação, modais, CSV, impressão e operação
  offline sem acessar o Zabbix.
- Controle compacto de 50, 100 ou 250 linhas por página na tabela operacional.
- Benchmark reproduzível de Excel e HTML com massas fictícias de 0, 10, 7.171
  e 20.000 registros, três execuções e comparação por mediana.
- Medições internas da exportação Excel para DataFrames, abas, estilos,
  larguras, tabelas, formatação condicional, gráficos e salvamento.
- Testes de equivalência da fonte compacta do HTML, paginação, grande volume,
  escape seguro, filtros, modal e CSV.
- Observabilidade centralizada com duração por etapa, chamadas da API, tamanhos,
  páginas, gargalos e avisos objetivos de desempenho.
- Resumo compacto de execução exibido no terminal em todas as gerações.
- Diagnóstico JSON seguro e opcional por meio de `--diagnostico`.
- Testes determinísticos com relógio, API, arquivos e falhas simulados, sem
  acesso ao Zabbix real.
- PDF Executivo 2.0 com capa, indicadores, rankings limitados, prioridades,
  recorrências, criticidade, integridade e conclusão em páginas compactas.
- Anexo técnico PDF separado e opcional por meio de `--pdf-detalhado`, com
  cabeçalho repetido, paginação e detalhamento completo dos eventos.
- Testes de volume, limite de rankings, seções vazias, paginação, nomes,
  acentuação e proteção contra URLs ou credenciais no PDF.
- Validação central de integridade antes da construção dos incidentes, com
  ajustes, descartes e avisos contabilizados sem expor dados sensíveis.
- Resumo canônico de integridade no HTML, Excel e PDF.
- Análise histórica da duração dos resolvidos, separada do passivo aberto.
- Logs seguros de coleta, processamento e exportação.

- Modelo testável para evento, incidente único e recorrência, com chave lógica
  determinística e normalizada.
- Casos fictícios para abertos, resolvidos, recuperação ausente, timestamps
  inválidos, agrupamento e indicadores exclusivos do passivo aberto.

### Corrigido

- Impressões acima de 5.000 registros filtrados agora são interrompidas com
  orientação clara para exportar o conjunto completo por CSV.
- Exportação Excel otimizada por reutilização de estilos, menos atribuições por
  célula e amostragem segura de larguras, preservando abas e acabamento.
- HTML operacional reduzido para uma única fonte compacta de dados e paginação
  de 100 linhas, sem limitar filtros, contadores, ordenação, modais ou CSV.
- O PDF principal não cresce mais conforme o total de eventos e não inclui a
  tabela operacional completa por padrão.
- Limites de conteúdo e quebra de texto evitam cortes e sobreposições no PDF.
- Duração de incidentes resolvidos agora termina na resolução e não continua
  envelhecendo a cada nova geração.
- Indicadores de idade e faixas temporais agora consideram somente incidentes
  abertos.
- Excel e detalhes do HTML agora distinguem abertura, resolução, duração total
  e idade do passivo aberto; o PDF usa a duração congelada da mesma linha.

### Planejado

- Ampliar a cobertura de testes automatizados.
- Criar rotina de geração agendada dos relatórios.
- Avaliar uma versão executável para uso em computadores sem conhecimento técnico.
- Melhorar a experiência de instalação e execução para outros usuários.

## 2026-06-25

### Adicionado

- Camada de inteligência executiva com distribuição temporal, padrões
  recorrentes e índice operacional de prioridade.
- Barra de ações no topo do relatório HTML.
- Modo apresentação para destacar indicadores, gráficos e rankings executivos.
- Alternância entre tema claro e tema escuro.
- Atalhos rápidos para navegar entre gráficos, filtros e tabela.

### Melhorado

- Exportação Excel, com aba de resumo executivo, rankings, filtros, tabelas,
  gráficos e cores por severidade/status.
- PDF executivo, com capa visual mais próxima do HTML e indicadores focados em
  incidentes abertos.
- Painel e modal da CONFEA VPN, com identidade visual própria, logo embutida,
  métricas de resumo e tabela mais legível.
- Cabeçalho do HTML, com composição visual mais ousada e indicadores executivos no próprio hero.
- Aplicação da nova logo da Techface no cabeçalho, com destaque visual e integração ao hero.
- Controle de tema, trocando o texto simples por "Modo lunar" e "Modo solar".
- Modo escuro, com maior integração visual entre cabeçalho, barra de ações, KPIs e gráficos.
- Acabamento dos microcomponentes, com barras de rolagem personalizadas e botão de fechar redesenhado.
- Padronização visual do cabeçalho "Detalhes" na tabela e refinamento do botão de fechar dos modais.
- Contraste do modo escuro em faixas de tempo, filtros, rankings e tabela.
- Legibilidade dos contadores dos filtros no modo escuro e ajuste dos ícones de modo lunar/solar.
- Substituição do texto "ZBX" por uma marca visual vermelha do Zabbix no painel do servidor.
- Aplicação das logos oficiais do Zabbix no painel e no modal do Servidor Zabbix.
- Contraste da tabela do modal "Servidor Zabbix" no modo escuro.
- Refinamento editorial e visual do painel de inteligência operacional, com
  linguagem mais executiva e síntese de criticidade, tendência e recorrência.
- Organização compacta do filtro do relatório, com busca no topo, resultados próximos e filtros principais lado a lado.
- Cards do cabeçalho atualizados para destacar geração, período analisado e autoria do Network Operations Center.
- Hierarquia visual do relatório HTML.
- Acabamento dos cards, filtros, tabela e modais.
- Leitura da tabela operacional, com destaque visual para prioridades altas.
- Experiência visual geral do relatório, mantendo a identidade em ciano e tons escuros.

## 2026-06-22

### Adicionado

- Testes automatizados para as regras de classificação de equipamentos, unidades e tipos de incidente.
- Testes automatizados para os cálculos de resumo, totais, rankings e faixas de tempo offline.
- Execução dos testes no GitHub Actions.
- Documentação do comando de testes no `COMANDOS.md`.

### Melhorado

- Performance dos filtros do relatório HTML.
- Filtro do relatório, com visual mais limpo e foco nas informações mais importantes.
- Painel do Servidor Zabbix, deixando os eventos separados das unidades escolares.

### Segurança

- Validação automatizada para evitar envio acidental de segredos ao repositório.
- Uso contínuo do script `scripts/check_secrets.py` antes dos commits.

## 2026-06-21

### Adicionado

- Gráficos executivos no relatório HTML.
- Mapa visual de severidade.
- Gráfico de equipamentos em destaque.
- Gráfico de faixas de tempo offline.
- Microinterações no HTML para melhorar a experiência de uso.
- Link direto para abrir o incidente no Zabbix a partir da janela de detalhes.

### Melhorado

- Organização dos indicadores principais.
- Padronização visual dos gráficos com uso predominante de ciano.
- Diferenciação das cores de severidade.
- Modais de detalhes dos incidentes.
- Uso da logo da Techface no relatório, mantendo o design original da marca.

## 2026-06-20

### Adicionado

- Relatório por tipo de equipamento.
- Scripts facilitadores para gerar relatórios por equipamento no Windows e no terminal.
- Guia rápido para uso do relatório por equipamento.
- Separação entre arquivos de estrutura HTML, CSS e JavaScript.

### Melhorado

- Organização do template HTML.
- Manutenção do relatório, reduzindo a concentração de código em um único arquivo.
- Experiência para outros usuários executarem o projeto.

## 2026-06-19

### Adicionado

- Filtros por unidade escolar, equipamento, severidade e tempo offline.
- Ranking de equipamentos mais afetados.
- Ranking de unidades mais afetadas.
- Ranking de hosts com mais incidentes.
- Ranking de tipos de incidente mais recorrentes.
- Janela de detalhes por incidente.
- Separação de eventos da CONFEA VPN.

### Melhorado

- Clareza do relatório para foco em incidentes abertos.
- Organização dos cartões de operação, tempo offline e severidade.
- Tabela de eventos com visual mais profissional.

## 2026-06-15

### Adicionado

- Geração do relatório em HTML.
- Geração do relatório em PDF.
- Geração de planilha Excel.
- Coleta de dados pela API do Zabbix.
- Organização dos dados por unidade, equipamento, severidade e status.
- Documentação operacional inicial.

### Segurança

- Criação do `.env.example`.
- Uso de `.env` para proteger credenciais reais.
- Instruções iniciais para evitar envio de tokens, senhas e URLs privadas.

## Convenção

As mudanças são agrupadas por tipo:

- **Adicionado**: novas funcionalidades.
- **Melhorado**: ajustes visuais, técnicos ou de usabilidade.
- **Corrigido**: correções de erro.
- **Segurança**: mudanças ligadas à proteção de credenciais e publicação segura.
- **Planejado**: próximos passos ainda não implementados.
