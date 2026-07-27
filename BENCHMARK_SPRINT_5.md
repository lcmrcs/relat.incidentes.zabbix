# Benchmark do Sprint 5

Este documento registra a comparação reproduzível das exportações Excel e HTML
com dados inteiramente fictícios. Nenhuma execução consulta o Zabbix.

## Método

- Ambiente: Python 3.12 em WSL 2, arquivos gravados no sistema temporário Linux.
- Cenários: 0, 10, 7.171 e 20.000 incidentes.
- Amostra: três execuções consecutivas por cenário.
- Resultado utilizado: mediana das três execuções.
- Linha de base: mesma massa fictícia, antes das otimizações do Sprint 5.
- O tempo total abaixo soma somente Excel e HTML; coleta, processamento e PDF
  não fazem parte deste benchmark de exportação.

Comando:

```bash
python scripts/benchmark_exports.py --runs 3 --volumes 0 10 7171 20000
```

## Resultado principal

| Registros | Excel antes | Excel depois | Tempo HTML antes | Tempo HTML depois | Tamanho HTML antes | Tamanho HTML depois | Linhas iniciais |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0,09s | 0,11s | 0,25s | 0,41s | 1,57 MB | 1,58 MB | 0 |
| 10 | 0,19s | 0,18s | 0,28s | 0,46s | 1,67 MB | 1,64 MB | 10 |
| 7.171 | 23,53s | 10,53s | 1,21s | 0,51s | 21,87 MB | 3,57 MB | 100 |
| 20.000 | 67,61s | 30,48s | 3,38s | 1,03s | 57,98 MB | 6,93 MB | 100 |

No cenário de referência de 7.171 registros:

- Excel: redução de **55,2%**, superando a meta mínima de 35% e ficando abaixo
  da meta desejada de 12 segundos;
- HTML: redução de **58,4%** no tempo de geração;
- tamanho do HTML: redução de **83,7%**;
- tempo combinado de Excel e HTML: de 24,74s para 11,04s, redução de **55,4%**;
- Excel final: aproximadamente 0,90 MB, sem remoção de abas ou recursos.

Em volumes vazios ou muito pequenos, a variação de inicialização do Python,
Jinja2 e `openpyxl` é maior que o trabalho útil. Por isso esses números não
devem ser interpretados como regressão prática.

## Evidências do gargalo

O perfil anterior à otimização atribuiu aproximadamente 66,9s do tempo
instrumentado à estilização da pasta de trabalho. Foram observadas mais de 540
mil atribuições de propriedades de estilo, com criação e registro repetidos de
objetos do `openpyxl`.

A implementação passou a:

- reutilizar estilos nomeados e suas estruturas internas já registradas;
- aplicar uma única estrutura de estilo por célula;
- medir separadamente DataFrames, escrita, estilos, larguras, tabelas,
  formatação condicional, gráficos e salvamento;
- limitar o cálculo automático de largura a uma amostra segura de 80 linhas;
- construir os DataFrames uma vez antes da escrita.

O custo remanescente em grandes volumes está principalmente na serialização
XML e no salvamento do XLSX. Remover a duplicação funcional das abas `Unidades`
e `Todos` reduziria esse custo, mas violaria os requisitos do relatório e não
foi feito.

## HTML

Antes, cada incidente era emitido como uma linha completa com atributos
duplicados, e o JavaScript reconstruía os dados a partir do DOM. Agora:

- existe uma única fonte compacta de dados serializada;
- o navegador materializa no máximo 100 linhas por página;
- busca, filtros, contadores e ordenação continuam operando sobre todos os
  registros;
- CSV usa todo o conjunto filtrado;
- modal usa os dados da linha materializada;
- impressão expande temporariamente o conjunto filtrado;
- o arquivo permanece autocontido e funcional offline.

Os testes automatizados verificam preservação dos campos, seções vazias,
grande volume, escape seguro do JSON e os caminhos de paginação, filtros,
modal, CSV e impressão.
