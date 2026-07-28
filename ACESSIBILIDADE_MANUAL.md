# Checklist Manual de Acessibilidade com NVDA

Este roteiro é recomendado antes de releases ou mudanças importantes na
interface. Ele não precisa ser executado em todo commit.

> A criação deste checklist não significa que o relatório já foi validado
> manualmente com NVDA.

## Preparação

- Use um relatório gerado exclusivamente com dados fictícios.
- Abra o HTML local no Microsoft Edge.
- Inicie o NVDA e mantenha mouse e touchpad sem uso durante o roteiro.
- Execute uma vez no modo solar e outra no modo lunar.

## Estrutura e leitura

- Confirme que o título “Relatório Executivo de Incidentes Zabbix” é anunciado.
- Navegue por títulos com `H` e valide a ordem das seções.
- Navegue por regiões com `D` e confirme cabeçalho, navegação e conteúdo principal.
- Verifique se imagens decorativas não geram anúncios inúteis.

## Filtros e tabela

- Acesse busca e filtros usando apenas `Tab` e `Shift+Tab`.
- Digite uma busca e confirme o anúncio da quantidade resultante.
- Combine e limpe filtros.
- Navegue pelos cabeçalhos da tabela e confirme nomes e relação com as células.
- Acione ordenação e paginação pelo teclado.
- Altere a quantidade de linhas por página.

## Modais

- Abra detalhes de um incidente com `Enter` ou `Espaço`.
- Confirme que o título e os campos do modal são anunciados.
- Verifique que o foco não alcança conteúdo atrás do modal.
- Feche com `Escape`.
- Confirme o retorno do foco ao botão que abriu o modal.
- Repita para Servidor Zabbix, CONFEA e Integridade dos Dados.

## Preferências e exportações

- Alterne entre modo solar e lunar pelo teclado.
- Confirme que o nome e o estado do controle continuam compreensíveis.
- Acesse CSV e impressão sem depender do mouse.
- Confirme que alertas ou limites de impressão são anunciados.

## Registro

Anote versão do NVDA, Edge, Windows, resolução, zoom, data e falhas encontradas.
Não inclua dados operacionais, URLs privadas, IPs ou credenciais no registro.
