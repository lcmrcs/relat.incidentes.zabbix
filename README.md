# Relatorio de Incidentes Zabbix

Projeto Python para consultar incidentes recentes no Zabbix e gerar relatorios
operacionais em Excel, HTML e PDF.

## Objetivo

O objetivo deste repositorio e automatizar a extracao de problemas do Zabbix,
classificar os incidentes por tipo de equipamento e gerar arquivos de relatorio
para acompanhamento tecnico.

Atualmente o projeto busca problemas dos ultimos 7 dias usando a API do Zabbix,
organiza os dados em uma tabela e exporta os resultados para a pasta
`reports/`.

## Estrutura do Projeto

```text
.
├── README.md
└── zabbix-report/
    ├── .env.example
    ├── .gitignore
    ├── requirements.txt
    ├── templates/
    │   └── report_template.html
    ├── test_zabbix_api.py
    └── zabbix_report.py
```

Arquivos principais:

- `zabbix-report/zabbix_report.py`: script principal de geracao dos relatorios.
- `zabbix-report/test_zabbix_api.py`: script simples para testar a conexao com a API.
- `zabbix-report/requirements.txt`: dependencias Python do projeto.
- `zabbix-report/.env.example`: modelo seguro para criar o arquivo local `.env`.
- `zabbix-report/templates/report_template.html`: template HTML do relatorio executivo.

## Requisitos

- Python 3.7 ou superior
- Acesso a API do Zabbix
- Token de API valido
- Dependencias listadas em `zabbix-report/requirements.txt`

Dependencias atuais:

- `requests`
- `pandas`
- `openpyxl`
- `python-dotenv`
- `jinja2`

## Configuracao

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Depois ajuste o arquivo `zabbix-report/.env` com as variaveis abaixo:

```env
ZABBIX_URL=https://seu-zabbix.example.com/api_jsonrpc.php
ZABBIX_TOKEN=seu_token_da_api
```

Importante: o arquivo `.env` deve permanecer fora do Git, pois contem
credenciais de acesso.

## Instalacao

Acesse a pasta do projeto:

```bash
cd zabbix-report
```

Crie e ative um ambiente virtual, caso ainda nao exista:

```bash
python3 -m venv venv
source venv/bin/activate
```

Instale as dependencias:

```bash
pip install -r requirements.txt
```

## Testar Conexao com o Zabbix

Antes de gerar relatorios, execute o teste de API:

```bash
python test_zabbix_api.py
```

Esse script valida se as variaveis do `.env` foram carregadas, consulta alguns
hosts via `host.get` e exibe o resultado no terminal.

## Gerar Relatorio

Com o ambiente configurado, execute:

```bash
python zabbix_report.py
```

O script principal:

1. Carrega `ZABBIX_URL` e `ZABBIX_TOKEN` do `.env`.
2. Consulta problemas recentes via metodo `problem.get`.
3. Filtra o periodo dos ultimos 7 dias.
4. Classifica os hosts por tipo de equipamento.
5. Monta um resumo executivo por severidade, equipamento e host.
6. Gera arquivos na pasta `reports/`.

Saidas esperadas:

```text
reports/report_AAAA-MM-DD.xlsx
reports/report_AAAA-MM-DD.html
reports/report_AAAA-MM-DD.pdf
```

O PDF e o HTML trazem uma visao amigavel para apresentacao, com indicadores
executivos no inicio e detalhamento tecnico dos incidentes em seguida.

## Classificacao de Equipamentos

O script tenta classificar automaticamente cada host usando palavras-chave no
nome do equipamento:

- Mikrotik
- Switch
- NVR
- Camera
- Terminal Facial
- Portal Detector de Metal
- Central de Alarme
- Outros

Essa classificacao pode ser refinada conforme o padrao real de nomes usado no
Zabbix.

## Proximos Passos Sugeridos

- Melhorar tratamento de erro no script principal, incluindo timeout e JSON invalido.
- Separar o codigo em funcoes para facilitar manutencao e testes.
- Adicionar filtros por severidade, grupo de hosts ou periodo customizado.
- Avaliar envio automatico por e-mail.
- Adicionar testes automatizados para classificacao e geracao de relatorios.

## Seguranca

- Nunca versionar `.env`, tokens ou senhas.
- Versionar apenas `.env.example`, sempre com valores ficticios.
- Manter `venv/`, `reports/`, caches e arquivos locais fora do Git.
- Usar um token de API com permissoes limitadas ao necessario.
- Testar primeiro em ambiente controlado antes de usar em producao.
