# Relatorio de Incidentes Zabbix

Projeto Python para consultar incidentes recentes no Zabbix e gerar relatorios
operacionais em Excel e HTML.

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
    ├── .env
    ├── .gitignore
    ├── requirements.txt
    ├── test_zabbix_api.py
    ├── venv/
    └── zabbix_report.py
```

Arquivos principais:

- `zabbix-report/zabbix_report.py`: script principal de geracao dos relatorios.
- `zabbix-report/test_zabbix_api.py`: script simples para testar a conexao com a API.
- `zabbix-report/requirements.txt`: dependencias Python do projeto.
- `zabbix-report/.env`: arquivo local de configuracao com URL e token do Zabbix.

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

Crie ou ajuste o arquivo `zabbix-report/.env` com as variaveis abaixo:

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
5. Gera arquivos na pasta `reports/`.

Saidas esperadas:

```text
reports/report_AAAA-MM-DD.xlsx
reports/report_AAAA-MM-DD.html
```

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

## Ponto Pendente Conhecido

O script principal referencia o template `templates/report_template.html`, mas
essa pasta ainda precisa ser criada para que a geracao do HTML funcione
corretamente.

Enquanto isso, a geracao do Excel ja esta estruturada, desde que a consulta ao
Zabbix retorne dados validos.

## Proximos Passos Sugeridos

- Criar `zabbix-report/templates/report_template.html`.
- Ajustar os caminhos do script para funcionarem independentemente da pasta de execucao.
- Melhorar tratamento de erro no script principal, incluindo timeout e JSON invalido.
- Separar o codigo em funcoes para facilitar manutencao e testes.
- Adicionar filtros por severidade, grupo de hosts ou periodo customizado.
- Avaliar exportacao em PDF ou envio automatico por e-mail.

## Seguranca

- Nunca versionar `.env`, tokens ou senhas.
- Usar um token de API com permissoes limitadas ao necessario.
- Testar primeiro em ambiente controlado antes de usar em producao.

