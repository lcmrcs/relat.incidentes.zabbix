# Validação da Sprint 6 em navegador real

- Data: 2026-07-28T17:34:22-03:00
- Navegador: Microsoft Edge 150.0.4078.99
- Sistema: Windows 11 / WSL (6.18.33.1-microsoft-standard-WSL2)
- Resolução: 1600x1000
- Abertura: arquivo HTML autocontido local (`file://`), modo headless.
- Dados: exclusivamente fictícios; nenhuma conexão com Zabbix.
- Impressão nativa: aprovada (8889.4 KB).

| Registros | Execuções | Resultado | HTML | DOM inicial | Carregamento | Busca | Filtro | Página | Ordenação |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 1 | Aprovado | 1.80 MB | 414 | 407.8 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms |
| 10 | 1 | Aprovado | 1.86 MB | 1173 | 396.7 ms | 180.1 ms | 0.0 ms | 0.0 ms | 0.0 ms |
| 7,171 | 3 | Aprovado | 3.77 MB | 2441 | 551.2 ms | 180.0 ms | 0.0 ms | 9.9 ms | 0.0 ms |
| 20,000 | 1 | Aprovado | 6.80 MB | 2441 | 652.6 ms | 180.0 ms | 0.0 ms | 9.9 ms | 0.0 ms |

As métricas são comparativas nesta máquina e não constituem metas universais.
A impressão acima de 5.000 linhas é interrompida com orientação para o CSV completo.
