# Segurança de Tokens e Credenciais

Este projeto usa credenciais para acessar a API do Zabbix. Por isso, alguns
cuidados são obrigatórios antes de compartilhar o repositório, enviar arquivos
ou permitir que outra pessoa execute o relatório.

## O Que Nunca Deve Ir para o GitHub

Nunca envie:

- `zabbix-report/.env`
- tokens do Zabbix;
- tokens do GitHub;
- senhas;
- arquivos de ambiente virtual, como `venv/` ou `venv-windows/`;
- relatórios com dados sensíveis, se eles não forem destinados ao público.

## Arquivo `.env`

Cada computador deve ter o seu próprio arquivo:

```text
zabbix-report/.env
```

Exemplo de conteúdo:

```env
ZABBIX_URL=https://seu-zabbix.example.com/api_jsonrpc.php
ZABBIX_TOKEN=cole_o_token_real_apenas_no_env_local
```

Esse arquivo é local e não deve ser compartilhado.

## Arquivo Seguro para Versionar

O único arquivo de ambiente que deve ficar no GitHub é:

```text
zabbix-report/.env.example
```

Ele deve conter apenas valores fictícios.

## Antes de Fazer Commit

Execute:

```bash
python scripts/check_secrets.py
```

Esse comando procura padrões comuns de vazamento, como:

- `ZABBIX_TOKEN` com valor real;
- token do GitHub começando com `gho_` ou `github_pat_`;
- senhas escritas diretamente em arquivos;
- arquivos `.env` fora da lista permitida.

Se o comando acusar risco, corrija antes de fazer commit.

## Se um Token For Exposto

Se algum token for enviado por engano:

1. Revogue o token imediatamente no sistema onde ele foi criado.
2. Gere um novo token.
3. Atualize o arquivo `.env` local.
4. Remova o segredo do histórico do Git, se necessário.

Trocar apenas o arquivo atual não é suficiente quando o segredo já entrou no
histórico do repositório.

## Boas Práticas

- Use tokens com permissão mínima necessária.
- Evite compartilhar prints que mostrem tokens ou URLs internas sensíveis.
- Não cole tokens em issues, commits, mensagens de pull request ou arquivos de
  documentação.
- Ao entregar o projeto para outra pessoa, envie o código sem `.env` e peça para
  ela configurar as credenciais localmente.
