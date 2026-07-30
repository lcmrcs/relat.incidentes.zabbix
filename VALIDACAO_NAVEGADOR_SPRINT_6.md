# Validação da Sprint 6 em navegador real

- Data: 2026-07-29T11:19:53-03:00
- Navegador: Microsoft Edge 150.0.4078.99
- Sistema: Windows 11 / WSL (11)
- Resolução: 1600x1000
- Abertura: arquivo HTML autocontido local (`file://`), modo headless.
- Dados: exclusivamente fictícios; nenhuma conexão com Zabbix.
- Impressão nativa: aprovada (8889.2 KB).

| Registros | Execuções | Resultado | HTML | DOM inicial | Carregamento | Busca | Filtro | Página | Ordenação |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 1/1 | Aprovado | 1.80 MB | 414 | 328.8 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms |
| 10 | 1/1 | Aprovado | 1.86 MB | 1173 | 503.7 ms | 183.7 ms | 1.9 ms | 0.0 ms | 97.0 ms |
| 7,171 | 3/3 | Aprovado | 3.77 MB | 2441 | 465.0 ms | 203.6 ms | 129.9 ms | 9.0 ms | 799.7 ms |
| 20,000 | 1/1 | Aprovado | 6.80 MB | 2441 | 588.5 ms | 239.3 ms | 142.8 ms | 8.2 ms | 1962.6 ms |

- Último cenário iniciado: 20000
- Última etapa concluída: all_scenarios
- Estado da execução: completed

As métricas são comparativas nesta máquina e não constituem metas universais.
A impressão acima de 5.000 linhas é interrompida com orientação para o CSV completo.
