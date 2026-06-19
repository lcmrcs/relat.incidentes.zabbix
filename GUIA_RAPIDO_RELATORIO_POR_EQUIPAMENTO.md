# Guia Rápido: Relatório por Equipamento

Este guia é para quem precisa gerar um relatório filtrado por qualquer tipo de
equipamento monitorado no Zabbix.

## Primeira Execução

1. Instale o Python no computador.
2. Baixe ou clone este projeto.
3. Abra a pasta do projeto.
4. Dê dois cliques em:

```text
ABRIR_RELATORIO_POR_EQUIPAMENTO.bat
```

Na primeira execução, o programa pode pedir:

- URL da API do Zabbix.
- Token da API do Zabbix.
- Nome do equipamento desejado.

As credenciais serão salvas no arquivo local:

```text
zabbix-report\.env
```

Esse arquivo não deve ser enviado para ninguém, pois contém credenciais.

## Equipamentos Aceitos

Digite o equipamento como aparece na classificação do relatório. Exemplos:

- `Terminal Facial`
- `Câmera`
- `Mikrotik`
- `Switch`
- `NVR`
- `Central de Alarme`
- `Portal Detector de Metal`

## Próximas Execuções

Depois da primeira configuração, basta abrir novamente:

```text
ABRIR_RELATORIO_POR_EQUIPAMENTO.bat
```

O script vai:

- perguntar qual equipamento deve ser filtrado;
- verificar o ambiente Python;
- criar uma `venv` própria do Windows, se necessário;
- instalar dependências, se necessário;
- buscar os incidentes abertos no Zabbix;
- filtrar somente o equipamento escolhido;
- gerar HTML, PDF e Excel;
- abrir o HTML automaticamente.

## Onde o Relatório Fica

Os arquivos gerados ficam em:

```text
zabbix-report\reports
```

O HTML terá um nome parecido com:

```text
report_2026-06-19_historico_abertos_terminal_facial.html
```

ou:

```text
report_2026-06-19_historico_abertos_camera.html
```

## Se Der Erro

Verifique:

- se o Python está instalado;
- se a internet está funcionando;
- se a URL do Zabbix está correta;
- se o token do Zabbix ainda é válido;
- se o arquivo `zabbix-report\.env` existe;
- se o nome do equipamento foi digitado corretamente.
