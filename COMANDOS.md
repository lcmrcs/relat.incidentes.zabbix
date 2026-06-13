# Comandos do Projeto

Este arquivo serve como guia rapido para executar, testar e atualizar o projeto
de relatorio de incidentes do Zabbix.

Os comandos estao organizados na ordem mais comum de uso.

## 1. Entrar na pasta do projeto

Use este comando antes de executar qualquer outro comando do projeto.

```bash
cd /mnt/c/Users/chip/Documents/relat.incidentes.zabbix
```

Funcao:
- Leva o terminal para a pasta principal do projeto.
- Garante que os caminhos dos arquivos sejam encontrados corretamente.

## 2. Ativar o ambiente virtual

```bash
source zabbix-report/venv/bin/activate
```

Funcao:
- Ativa o ambiente Python do projeto.
- Faz o terminal usar as bibliotecas instaladas dentro da pasta `venv`.
- Evita misturar dependencias deste projeto com outras instalacoes do Python.

Depois de ativar, o terminal geralmente mostra algo como:

```text
(venv)
```

## 3. Testar conexao com a API do Zabbix

```bash
python zabbix-report/test_zabbix_api.py
```

Funcao:
- Verifica se o arquivo `.env` esta configurado.
- Testa se a URL do Zabbix esta acessivel.
- Testa se o token da API esta funcionando.
- Mostra alguns hosts encontrados no Zabbix.

Use este comando quando:
- Alterar o `.env`.
- Suspeitar de problema de conexao.
- Quiser confirmar se o Zabbix esta respondendo antes de gerar relatorios.

## 4. Ver ajuda do gerador de relatorio

```bash
python zabbix-report/zabbix_report.py --help
```

Funcao:
- Mostra as opcoes disponiveis no script de relatorio.
- Ajuda a lembrar como usar argumentos como `--periodo`.

## 5. Gerar relatorio com periodo padrao

```bash
python zabbix-report/zabbix_report.py
```

Funcao:
- Gera o relatorio usando o periodo padrao configurado no script.
- Atualmente o padrao e `7d`, ou seja, ultimos 7 dias.
- Cria arquivos HTML, PDF e Excel na pasta `zabbix-report/reports`.

## 6. Gerar relatorio das ultimas 24 horas

```bash
python zabbix-report/zabbix_report.py --periodo 24h
```

Funcao:
- Busca eventos de problema das ultimas 24 horas.
- Gera arquivos com o sufixo `_24h`.

Exemplo de arquivo gerado:

```text
zabbix-report/reports/report_2026-06-12_24h.html
```

## 7. Gerar relatorio de 2 dias

```bash
python zabbix-report/zabbix_report.py --periodo 2d
```

Funcao:
- Busca eventos de problema dos ultimos 2 dias.
- Util para analisar um intervalo maior que 24 horas sem chegar em uma semana.

## 8. Gerar relatorio de 5 dias

```bash
python zabbix-report/zabbix_report.py --periodo 5d
```

Funcao:
- Busca eventos de problema dos ultimos 5 dias.
- Util para acompanhar incidentes acumulados durante a semana.

## 9. Gerar relatorio de 7 dias

```bash
python zabbix-report/zabbix_report.py --periodo 7d
```

Funcao:
- Busca eventos de problema dos ultimos 7 dias.
- Equivale ao periodo semanal.

## 10. Gerar relatorio desde uma data especifica

```bash
python zabbix-report/zabbix_report.py --desde 2026-01-01
```

Funcao:
- Busca eventos de problema desde a data informada ate o momento atual.
- Use o formato `AAAA-MM-DD`.
- E mais seguro que buscar o historico completo quando o Zabbix tem muitos dados.

## 11. Gerar relatorio do historico completo

```bash
python zabbix-report/zabbix_report.py --periodo historico
```

Funcao:
- Busca eventos de problema desde o registro mais antigo disponivel no Zabbix
  ate o momento atual.

Atencao:
- Este comando pode demorar bastante.
- Pode gerar arquivos HTML, PDF e Excel muito grandes.
- Use primeiro `--desde` se quiser controlar melhor o tamanho do relatorio.

Para buscar o historico completo contando apenas incidentes abertos:

```bash
python zabbix-report/zabbix_report.py --periodo historico --status abertos
```

Funcao:
- Busca o historico disponivel no Zabbix.
- Remove eventos ja resolvidos do relatorio.
- Mostra somente eventos/incidentes que continuam abertos.

Observacao:
- Este e o comando recomendado para o relatorio operacional atual.
- O HTML foi organizado para acompanhar incidentes abertos, com filtros por
  unidade escolar, equipamento, severidade, tempo offline e prioridade.
- Como todos os registros deste modo estao abertos, o filtro de situacao fica
  oculto automaticamente para evitar duplicidade entre `Tudo` e `Aberto`.

## 12. Ver arquivos modificados no Git

```bash
git status
```

Funcao:
- Mostra quais arquivos foram alterados.
- Mostra quais arquivos estao prontos para commit.
- Ajuda a evitar subir arquivos errados para o GitHub.

## 13. Preparar arquivos para commit

```bash
git add .
```

Funcao:
- Adiciona todas as alteracoes atuais para o proximo commit.

Atencao:
- Antes de usar `git add .`, rode `git status`.
- Confira se nao existem arquivos gerados grandes, temporarios ou secretos.

Para adicionar arquivos especificos:

```bash
git add zabbix-report/zabbix_report.py
git add zabbix-report/templates/report_template.html
```

## 14. Criar commit

```bash
git commit -m "descreva aqui o que foi alterado"
```

Funcao:
- Salva um ponto no historico do projeto.
- Registra as alteracoes preparadas com `git add`.

Exemplo:

```bash
git commit -m "feat: melhora filtros do relatorio Zabbix"
```

## 15. Enviar alteracoes para o GitHub

```bash
git push origin main
```

Funcao:
- Envia os commits locais para o repositorio no GitHub.

Quando pedir usuario:

```text
lcmrcs
```

Quando pedir senha:

```text
cole o token do GitHub
```

Observacao:
- O GitHub nao usa mais senha normal para `git push`.
- Use um Personal Access Token.

## 16. Fluxo rapido do dia a dia

Quando quiser testar e gerar um relatorio, use:

```bash
cd /mnt/c/Users/chip/Documents/relat.incidentes.zabbix
source zabbix-report/venv/bin/activate
python zabbix-report/test_zabbix_api.py
python zabbix-report/zabbix_report.py --periodo historico --status abertos
```

Quando quiser salvar e subir alteracoes:

```bash
git status
git add .
git commit -m "mensagem do commit"
git push origin main
```
