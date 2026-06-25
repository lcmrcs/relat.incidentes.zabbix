# Changelog

Histórico das principais evoluções do projeto **Relatório Executivo de Incidentes Zabbix**.

Este arquivo registra mudanças relevantes de forma simples, para facilitar acompanhamento técnico, prestação de contas e evolução do projeto.

## Em Desenvolvimento

### Planejado

- Melhorar a geração do PDF executivo, com layout mais fiel ao HTML.
- Ampliar a cobertura de testes automatizados.
- Criar rotina de geração agendada dos relatórios.
- Avaliar uma versão executável para uso em computadores sem conhecimento técnico.
- Melhorar a experiência de instalação e execução para outros usuários.

## 2026-06-25

### Adicionado

- Barra de ações no topo do relatório HTML.
- Modo apresentação para destacar indicadores, gráficos e rankings executivos.
- Alternância entre tema claro e tema escuro.
- Atalhos rápidos para navegar entre gráficos, filtros e tabela.

### Melhorado

- Cabeçalho do HTML, com composição visual mais ousada e indicadores executivos no próprio hero.
- Aplicação da nova logo da Techface no cabeçalho, com destaque visual e integração ao hero.
- Controle de tema, trocando o texto simples por "Modo lunar" e "Modo solar".
- Modo escuro, com maior integração visual entre cabeçalho, barra de ações, KPIs e gráficos.
- Acabamento dos microcomponentes, com barras de rolagem personalizadas e botão de fechar redesenhado.
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
