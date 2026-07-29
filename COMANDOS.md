# Guia Operacional do Relatório Executivo de Incidentes Zabbix

Este guia mostra os comandos principais para executar, gerar relatórios,
abrir arquivos, validar alterações e atualizar o GitHub.

Use este arquivo como referência rápida quando quiser puxar um relatório novo
ou fazer ajustes pequenos no projeto.

## 1. Entrar na pasta do projeto

Execute sempre antes dos outros comandos:

```bash
cd /mnt/c/Users/chip/Desktop/lcmrcsWorkspace/relat.incidentes.zabbix
```

Funcao:
- Coloca o terminal na pasta principal do projeto.
- Evita erro de caminho ao executar scripts.

## 2. Ativar o ambiente virtual

```bash
source zabbix-report/venv/bin/activate
```

Funcao:
- Ativa o Python isolado do projeto.
- Faz o terminal usar as bibliotecas instaladas na `venv`.

Sinal de que deu certo:

```text
(venv)
```

Para sair da venv:

```bash
deactivate
```

## 3. Testar conexao com o Zabbix

```bash
python zabbix-report/test_zabbix_api.py
```

Use quando:
- O relatorio falhar.
- O token do Zabbix for alterado.
- A API parecer lenta ou indisponivel.
- Voce quiser confirmar que o `.env` esta correto.

## 4. Tela inicial para gerar relatorios

Este e o caminho mais facil para gerar relatorios sem decorar comandos.

No Windows:

```text
abrir_tela_relatorio.bat
```

No Linux ou WSL:

```bash
./abrir_tela_relatorio.sh
```

Funcao:
- Abre uma tela local no navegador.
- Permite escolher periodo, situacao, equipamento e quantidade de relatorios
  mantidos.
- Permite filtrar por codigo ou nome de unidade escolar.
- Executa o gerador principal por tras da tela.
- Mostra links para abrir HTML, Excel e PDF ao finalizar.

Endereco usado pela tela:

```text
http://127.0.0.1:8765/
```

Observacao:
- A janela do terminal precisa continuar aberta enquanto voce usa a tela.
- Para encerrar a tela local, pressione `Ctrl+C` no terminal.

## 5. Comando principal do relatorio atual

Este e o comando mais importante do projeto:

```bash
python zabbix-report/zabbix_report.py --periodo historico --status abertos
```

Funcao:
- Busca todos os incidentes ainda abertos.
- Ignora incidentes ja resolvidos.
- Gera HTML, PDF e Excel atualizados.
- Mostra o estado operacional atual do Zabbix.
- Remove relatórios antigos da pasta `reports/`, mantendo por padrão apenas o
  conjunto mais recente.

Arquivos gerados:

```text
zabbix-report/reports/
```

Formatos:
- `.html`: relatorio interativo com filtros.
- `.pdf`: relatorio executivo compacto para envio.
- `.xlsx`: planilha com os dados.

Para gerar também o anexo técnico PDF com todos os eventos:

```bash
python zabbix-report/zabbix_report.py --periodo historico --status abertos --pdf-detalhado
```

Arquivos PDF:

```text
report_AAAA-MM-DD_periodo.pdf
report_AAAA-MM-DD_periodo_anexo_tecnico.pdf
```

Sem `--pdf-detalhado`, somente o PDF executivo é criado. O HTML e o Excel
continuam contendo o detalhamento operacional completo.

Para gerar também o diagnóstico técnico seguro:

```bash
python zabbix-report/zabbix_report.py --periodo historico --status abertos --diagnostico
```

Arquivo adicional:

```text
report_AAAA-MM-DD_periodo_diagnostico.json
```

O resumo de desempenho sempre aparece no terminal. O JSON só é criado com
`--diagnostico` e contém tempos por etapa, chamadas da API, tamanhos, páginas,
gargalo e avisos, sem credenciais, URLs, IPs ou conteúdo dos incidentes.

Os argumentos podem ser combinados:

```bash
python zabbix-report/zabbix_report.py --periodo 7d --pdf-detalhado --diagnostico
```

Para guardar mais de um conjunto de relatórios, use:

```bash
python zabbix-report/zabbix_report.py --periodo historico --status abertos --manter-relatorios 3
```

Funcao:
- Mantem os 3 conjuntos mais recentes em `zabbix-report/reports/`.
- Evita que a pasta acumule relatórios antigos demais.
- Use apenas quando precisar comparar relatórios de execuções anteriores.

## 6. Gerar relatorio por equipamento

Use quando quiser um relatório específico de um tipo de equipamento, sem
alterar o relatório principal.

Exemplo para Terminal Facial:

```bash
python zabbix-report/zabbix_report.py --periodo historico --status abertos --equipamento "Terminal Facial"
```

Funcao:
- Mantem apenas incidentes de Terminal Facial.
- Gera HTML, PDF e Excel separados.
- Adiciona o nome do equipamento no periodo e no nome do arquivo.

Exemplos para outros equipamentos:

```bash
python zabbix-report/zabbix_report.py --periodo historico --status abertos --equipamento "Câmera"
python zabbix-report/zabbix_report.py --periodo historico --status abertos --equipamento "Mikrotik"
```

Exemplo por unidade escolar:

```bash
python zabbix-report/zabbix_report.py --periodo historico --status abertos --unidade 1011
```

## 6.1. Atalho para relatório por equipamento

Use este atalho quando outra pessoa precisar gerar um relatório filtrado por
equipamento, sem decorar o comando completo.

No Windows, basta abrir:

```text
ABRIR_RELATORIO_POR_EQUIPAMENTO.bat
```

No Linux ou WSL:

```bash
./gerar_relatorio_equipamento.sh
```

Função:
- Verifica se existe `zabbix-report/.env`.
- Cria o `.env` na primeira execução, se necessário.
- Cria uma `venv` própria do Windows, se necessário.
- Instala as dependências do projeto.
- Pergunta qual equipamento deve ser filtrado.
- Executa o relatório com `--equipamento`.
- Abre o HTML mais recente gerado.

Guia simples para enviar a outra pessoa:

```text
GUIA_RAPIDO_RELATORIO_POR_EQUIPAMENTO.md
```

## 6. Gerar relatorio das ultimas 24h

```bash
python zabbix-report/zabbix_report.py --periodo 24h
```

Funcao:
- Busca eventos das ultimas 24 horas.
- Inclui abertos e resolvidos, salvo se voce usar `--status abertos`.

Somente abertos das ultimas 24h:

```bash
python zabbix-report/zabbix_report.py --periodo 24h --status abertos
```

## 7. Gerar relatorios por outros periodos

```bash
python zabbix-report/zabbix_report.py --periodo 2d
python zabbix-report/zabbix_report.py --periodo 5d
python zabbix-report/zabbix_report.py --periodo 7d
python zabbix-report/zabbix_report.py --periodo 30d
```

Funcao:
- Busca eventos dentro do intervalo informado.
- `h` significa horas.
- `d` significa dias.

## 8. Gerar relatorio desde uma data especifica

```bash
python zabbix-report/zabbix_report.py --desde 2026-06-01
```

Funcao:
- Busca eventos desde a data informada ate agora.
- Use o formato `AAAA-MM-DD`.
- E util quando o historico completo estiver pesado.

## 9. Abrir o HTML gerado

Abra pelo Explorer:

```text
C:\Users\chip\Desktop\lcmrcsWorkspace\relat.incidentes.zabbix\zabbix-report\reports
```

Ou pelo terminal, ajustando o nome do arquivo:

```bash
cmd.exe /c start "" "C:\Users\chip\Desktop\lcmrcsWorkspace\relat.incidentes.zabbix\zabbix-report\reports\report_2026-06-15_historico_abertos.html"
```

## 10. Validar o HTML em navegador real

No WSL, com o ambiente virtual ativo:

```bash
python scripts/validate_html_browser.py
```

O comando usa Edge ou Chrome já instalado no Windows, abre somente relatórios
fictícios locais e valida os cenários de 0, 10, 7.171 e 20.000 registros. Os
resultados ficam em:

```text
VALIDACAO_NAVEGADOR_SPRINT_6.json
VALIDACAO_NAVEGADOR_SPRINT_6.md
```

Essa rotina não acessa o Zabbix e não é necessária para a geração normal.

## 11. Validar regressão visual e acessibilidade

Executar tudo:

```bash
python scripts/validate_visual_accessibility.py
```

Executar separadamente:

```bash
python scripts/validate_visual_accessibility.py --visual-only
python scripts/validate_visual_accessibility.py --accessibility-only
```

Revisar diferenças geradas:

```text
artifacts/visual-accessibility/current/
artifacts/visual-accessibility/diffs/
```

Atualizar baselines somente depois de revisar e aprovar a mudança:

```bash
python scripts/validate_visual_accessibility.py --visual-only --update-baselines
```

As capturas usam somente dados fictícios. A validação cobre os modos solar e
lunar em 390x844, 768x1024 e 1600x1000, além do cenário desktop com zoom de
200% e preferência por movimento reduzido.

## 12. Validar o mesmo conjunto usado no CI

Qualidade e testes:

```bash
ruff check .
git ls-files -z '*.py' | xargs -0 -n 1 black --check
pytest
python scripts/check_secrets.py
git diff --check
```

Compatibilidade temporal no WSL/Linux:

```bash
python -m pytest \
  zabbix-report/tests/test_time_utils.py \
  zabbix-report/tests/test_incident_model.py \
  zabbix-report/tests/test_data_integrity.py \
  zabbix-report/tests/test_summary.py
```

No PowerShell ou terminal do Windows:

```powershell
python -m pytest zabbix-report/tests/test_time_utils.py zabbix-report/tests/test_incident_model.py zabbix-report/tests/test_data_integrity.py zabbix-report/tests/test_summary.py
```

Navegador:

```bash
python scripts/validate_html_browser.py
python scripts/validate_visual_accessibility.py
```

Os workflows também podem ser iniciados manualmente na aba **Actions** do
GitHub. Consulte `POLITICA_BASELINES.md` antes de aprovar qualquer alteração
nas imagens de referência.

## 13. O que existe no HTML

O HTML atual possui:
- Resumo executivo.
- Filtro por unidade escolar.
- Filtro por equipamento.
- Filtro por severidade.
- Filtro por tempo offline.
- Prioridade operacional.
- Tipos de incidente consolidados.
- Hosts com mais incidentes.
- Unidades mais afetadas.
- Janela separada para Servidor Zabbix.
- Janela separada para CONFEA VPN.
- Exportacao CSV dos dados filtrados.

## 14. Tipos de incidente consolidados

O painel "Tipos de Incidente" nao deve contar cada texto tecnico isolado do
Zabbix. Ele consolida familias de problemas.

Exemplos:
- `Unavailable by ICMP ping`
- `High ICMP ping response time`
- `High ICMP ping loss`
- `No SNMP data collection`
- `Temperature above threshold`
- `High bandwidth usage`
- `Ethernet lower speed`
- `Interface down`

Arquivo onde isso e ajustado:

```text
zabbix-report/classifiers.py
```

Funcao:

```python
def classify_incident_type(incident):
```

Quando aparecer um novo texto do Zabbix que deveria entrar em uma familia
existente, adicione uma regra nessa funcao.

## 15. Classificacao de equipamentos

Arquivo:

```text
zabbix-report/classifiers.py
```

Funcao:

```python
def classify_equipment(host):
```

Ordem operacional usada no filtro:
- Mikrotik
- Switch
- NVR
- Central de Alarme
- Terminal Facial
- Portal Detector de Metal
- Camera

Observacao:
- O painel "Equipamentos Mais Afetados" ordena por maior volume.
- O filtro "Equipamento" segue a ordem operacional acima.

## 13. Arquivos principais do projeto

```text
zabbix-report/zabbix_report.py
```

Coordena o fluxo principal: consulta Zabbix, processa dados, gera Excel, HTML e
PDF.

```text
zabbix-report/zabbix_api.py
```

Centraliza chamadas para a API do Zabbix.

```text
zabbix-report/observability.py
```

Centraliza tempos, métricas seguras, avisos de gargalo e diagnóstico JSON.

```text
zabbix-report/classifiers.py
```

Guarda regras de classificacao de unidade, equipamento e tipo de incidente.

```text
zabbix-report/summary.py
```

Calcula totais, rankings, indicadores, tempo offline e listas do resumo.

```text
zabbix-report/templates/report_template.html
```

Controla o visual e a interatividade do HTML.

```text
zabbix-report/pdf_report.py
```

Gera o PDF executivo compacto e o anexo técnico opcional.

```text
COMANDOS.md
```

Este guia.

## 14. Validar codigo depois de alterar

Sempre que mexer em Python:

```bash
python -m py_compile zabbix-report/*.py
```

Rodar os testes automatizados:

```bash
python -m unittest discover -s zabbix-report/tests -p "test_*.py"
```

Funcao:
- Confere se as classificacoes de equipamento, unidade e tipo de incidente continuam corretas.
- Confere se os totais, rankings e faixas de tempo offline continuam sendo calculados corretamente.
- Ajuda a descobrir rapidamente se uma melhoria quebrou alguma regra importante do relatorio.

Verificar espacos problemáticos no Git:

```bash
git diff --check
```

Ver resumo das mudancas:

```bash
git diff --stat
```

### Benchmark local das exportacoes

Use somente para medir Excel e HTML com dados ficticios, sem acessar o Zabbix:

```bash
python scripts/benchmark_exports.py --runs 3 --volumes 0 10 7171 20000
```

Para salvar o resultado bruto:

```bash
python scripts/benchmark_exports.py --runs 3 --volumes 0 10 7171 20000 --output benchmark.json
```

O comparativo validado do Sprint 5 esta em `BENCHMARK_SPRINT_5.md`.

## 15. Ver arquivos alterados

```bash
git status
```

Funcao:
- Mostra arquivos modificados.
- Mostra arquivos novos.
- Mostra commits locais ainda nao enviados.

## 16. Criar commit

Antes:

```bash
git status
```

Adicionar arquivos:

```bash
git add .
```

Criar commit:

```bash
git commit -m "mensagem clara do que mudou"
```

Exemplos:

```bash
git commit -m "feat: adiciona ranking de tipos de incidente"
git commit -m "fix: consolida tipos de incidente no ranking"
git commit -m "docs: atualiza guia operacional"
```

## 17. Enviar para o GitHub

```bash
git push origin main
```

Se pedir usuario:

```text
lcmrcs
```

Se pedir senha:

```text
cole o token do GitHub
```

Observacao:
- O GitHub nao aceita mais senha normal.
- Use Personal Access Token.
- Nunca cole token em arquivo do projeto.

## 18. Fazer pacote para supervisor

Arquivos recomendados:
- PDF: versao formal.
- HTML: versao interativa.
- XLSX: dados brutos.

Pasta usada anteriormente:

```text
entrega_supervisor/
```

Essa pasta fica fora do Git pelo `.gitignore` da raiz.

## 19. Se o script ficar lento

Use um periodo menor:

```bash
python zabbix-report/zabbix_report.py --periodo 24h
```

Ou use uma data inicial:

```bash
python zabbix-report/zabbix_report.py --desde 2026-06-01
```

Para o estado operacional atual, prefira:

```bash
python zabbix-report/zabbix_report.py --periodo historico --status abertos
```

## 20. Se der timeout

Tente nesta ordem:

```bash
python zabbix-report/test_zabbix_api.py
python zabbix-report/zabbix_report.py --periodo 24h
python zabbix-report/zabbix_report.py --desde 2026-06-01 --status abertos
python zabbix-report/zabbix_report.py --periodo historico --status abertos
```

Se continuar falhando:
- Verifique internet/VPN.
- Verifique URL e token no `.env`.
- Aguarde alguns minutos e tente novamente.

## 21. Regra de seguranca

Nunca envie para o GitHub:
- `.env`
- token do Zabbix
- token do GitHub
- senhas
- arquivos temporarios
- pacotes de entrega com dados sensiveis

Antes de criar um commit, rode:

```bash
python scripts/check_secrets.py
```

Funcao:
- Procura tokens e senhas em arquivos do projeto.
- Avisa se existir `.env` em lugar perigoso.
- Ajuda a evitar vazamento acidental de credenciais.

Guia completo:

```text
SEGURANCA.md
```

## 22. Fluxo rapido do dia a dia

Gerar relatorio atual:

```bash
cd /mnt/c/Users/chip/Desktop/lcmrcsWorkspace/relat.incidentes.zabbix
source zabbix-report/venv/bin/activate
python zabbix-report/zabbix_report.py --periodo historico --status abertos
```

Validar alteracoes:

```bash
python -m py_compile zabbix-report/*.py
python -m unittest discover -s zabbix-report/tests -p "test_*.py"
git diff --check
git status
```

O diretório `zabbix-report/tests` usa apenas dados fictícios. O arquivo
`zabbix-report/test_zabbix_api.py` é uma verificação manual de conectividade e
não faz parte da suíte automatizada.

O gerador registra no terminal somente etapas, quantidades e categorias de
integridade. Credenciais, URLs privadas e payloads não são incluídos nos logs.

Salvar e enviar:

```bash
git add .
git commit -m "mensagem clara"
git push origin main
```

## 23. Comando mais importante

Se voce esquecer todo o resto, lembre deste:

```bash
cd /mnt/c/Users/chip/Desktop/lcmrcsWorkspace/relat.incidentes.zabbix
source zabbix-report/venv/bin/activate
python zabbix-report/zabbix_report.py --periodo historico --status abertos
```
