# Validação do CI — Sprint 9

## Situação

Auditoria realizada em 28/07/2026 sobre os workflows:

- `Qualidade contínua`;
- `Validação em navegador`.

A ativação inicial ocorreu na `main` antes desta Sprint, mediante autorização.
O primeiro erro de instalação foi corrigido no commit `6206540`, trocando a
referência inexistente da raiz por `zabbix-report/requirements.txt`.

Esta evidência registra as execuções reais já disponíveis, a falha visual
encontrada e a correção local ainda não publicada. A Sprint 9 somente poderá ser
considerada concluída depois que a correção executar com sucesso em uma branch
dedicada e em uma pull request.

## Auditoria de publicação

- Árvore inicialmente limpa e sincronizada com `origin/main`.
- `.env`, relatórios HTML/Excel/PDF e artefatos locais estão ignorados.
- Nenhum arquivo operacional, log sensível ou caminho pessoal foi selecionado.
- `scripts/check_secrets.py`: aprovado.
- `git diff --check`: aprovado.
- Baselines rastreadas: 11 imagens, sem alterações.
- Evidências e fixtures usam apenas hosts, unidades, eventos e datas fictícios.

Arquivos previstos para a próxima publicação:

- `scripts/validate_visual_accessibility.py`;
- `zabbix-report/tests/test_visual_accessibility.py`;
- `VALIDACAO_CI_SPRINT_9.md`;
- evidências sanitizadas regeneradas pelos validadores.

## Primeira execução real

### Qualidade contínua

Execução: `30392883639`, commit `6206540`.

| Job | Sistema | Resultado | Duração |
| --- | --- | --- | ---: |
| Qualidade Python | Ubuntu 24.04.4 LTS | Aprovado | 28 s |
| Testes | Ubuntu 24.04.4 LTS | Aprovado | 27 s |
| Segurança | Ubuntu 24.04.4 LTS | Aprovado | 5 s |

- Tempo do workflow: 31 s.
- Python: CPython 3.12.13.
- Runner: `ubuntu-24.04`, imagem `20260720.247.2`.
- Ruff, Black, compilação e quatro testes estruturais: aprovados.
- Cache pip: primeira execução sem cache disponível.
- Os jobs paralelos tentaram gravar a mesma chave ao final; um deles informou
  que outro job já estava criando o cache. O aviso não afetou o resultado.
- Artefatos: nenhum, conforme esperado para este workflow.

### Validação em navegador

Execução: `30392885759`, commit `6206540`.

| Job | Sistema | Resultado | Duração |
| --- | --- | --- | ---: |
| Detectar mudanças visuais | Ubuntu | Aprovado | 4 s |
| HTML no Navegador | Windows Server 2025 | Aprovado | 1 min 46 s |
| Regressão Visual | Windows Server 2025 | Falhou | 1 min 27 s |
| Acessibilidade | Windows Server 2025 | Aprovado | 1 min 9 s |

- Tempo do workflow: 2 min 5 s.
- Python no Windows: CPython 3.12.10.
- Navegador: Microsoft Edge 150.0.4078.65.
- Runner: `windows-2025-vs2026`, imagem `20260714.173.1`.
- Cache pip: não encontrado; a instalação consumiu de 36 a 39 segundos por job.
- Nenhum job esperado foi ignorado.
- Etapas de upload de falha foram ignoradas nos jobs aprovados, como previsto.
- A detecção marcou as alterações como relevantes e executou os três jobs
  Windows.

## Diagnóstico da regressão visual

Sete das onze capturas foram aprovadas. Quatro falharam:

| Captura | Diferença |
| --- | ---: |
| `mobile_solar_tabela` | 4,7059% |
| `desktop_solar_zabbix` | 1,1906% |
| `desktop_lunar_confea` | 0,5338% |
| `desktop_lunar_grande_volume` | 16,7366% |

A revisão das imagens atuais, esperadas e de diferença confirmou:

- tabelas capturadas durante a primeira composição do layout, com lacunas
  transitórias entre linhas;
- diferenças de rasterização de fontes entre o Edge 150.0.4078.65 do runner e
  o Edge 150.0.4078.99 usado na criação local das referências;
- nenhuma alteração de HTML, CSS, conteúdo, cálculos ou identidade visual;
- nenhuma justificativa para atualizar as baselines.

Correção mínima aplicada somente ao validador:

- remover a captura anterior antes de chamar o navegador;
- forçar o cálculo de layout da seção isolada antes do screenshot;
- normalizar deslocamentos de rasterização de até um pixel ao comparar a
  captura com pixels vizinhos da baseline;
- manter a tolerância original de `0,35%` e o limite de diferença por canal;
- continuar proibindo atualização automática das baselines.

Validação local posterior: 11 de 11 capturas aprovadas, com maior diferença de
`0,0154%`.

## Artefatos

Artefatos reais da execução `30392885759`:

| Artefato | Conteúdo | Tamanho | Retenção |
| --- | --- | ---: | ---: |
| `falha-regressao-visual` | JSON, Markdown, atuais, diffs e baselines | 10.669.099 bytes | 5 dias |
| `resumo-html-navegador` | JSON e Markdown | 1.482 bytes | 3 dias |
| `resumo-acessibilidade` | JSON e Markdown | 1.389 bytes | 3 dias |

O artefato visual real possuía 28 arquivos. A inspeção não encontrou tokens,
credenciais, IPs privados ou URLs privadas. As imagens revisadas apresentam
somente dados fictícios.

Uma falha controlada de acessibilidade também foi simulada localmente em
diretório temporário. O pacote continha:

- resumo Markdown;
- resultado JSON;
- violação fictícia;
- navegador, sistema, resolução e tema.

A configuração do workflow publica esse pacote por cinco dias quando o job
falha. O estado válido foi preservado após a simulação.

## Validação local final

- Testes: 65 aprovados, 1 ignorado, 18 subtestes aprovados.
- Testes estruturais dos workflows: 4 aprovados.
- Ruff: aprovado.
- Black em modo de verificação: aprovado.
- Compilação Python: aprovada.
- Verificação de segredos: aprovada.
- YAML: dois workflows válidos.
- Smoke test no Edge: 0, 10, 7.171 e 20.000 registros aprovados.
- Regressão visual: 11 de 11 baselines aprovadas.
- Acessibilidade automática: seis cenários aprovados, sem avisos.
- Baselines: 11 arquivos rastreados e não modificados.
- Zabbix real: não acessado.

## Tempos e pontos de otimização

Há apenas uma execução bem-sucedida do workflow de qualidade e uma execução
parcial do workflow de navegador. Portanto, ainda não existe amostra suficiente
para calcular média ou variação confiáveis.

Observações reais:

- qualidade: 31 segundos;
- navegador: 2 min 5 s, encerrado com falha visual;
- job mais demorado: HTML no Navegador, 1 min 46 s;
- maior custo comum: instalação sem cache nos jobs Windows;
- cache frio também consumiu aproximadamente 15 segundos nos jobs Linux;
- otimização futura possível: evitar disputa de gravação da mesma chave de
  cache entre jobs paralelos e medir uma segunda execução com cache aquecido.

Esses pontos não justificam mudança de arquitetura nesta Sprint.

## Proteção recomendada para `main`

Checks recomendados como obrigatórios:

- `Qualidade Python`;
- `Testes`;
- `Segurança`;
- `Regressão Visual`;
- `Acessibilidade`.

Impacto: um pull request não poderá ser integrado enquanto código, testes,
segurança, aparência ou acessibilidade apresentarem falha. A manutenção exige
preservar os nomes dos jobs ou atualizar as regras quando eles forem
renomeados.

Procedimento recomendado:

1. ativar proteção somente depois da pull request da Sprint 9 ficar verde;
2. exigir branch atualizada antes do merge;
3. não permitir atualização automática de baselines;
4. revisar manualmente artefatos de qualquer falha visual;
5. não ignorar checks administrativos sem registrar a justificativa.

Nenhuma proteção ou regra externa foi ativada automaticamente.

## NVDA e limitações

O checklist manual de NVDA permanece em `ACESSIBILIDADE_MANUAL.md`.

O teste com NVDA não foi realizado nesta Sprint. Versão, navegador, fluxo e
resultado não podem ser registrados como aprovados até uma execução manual pelo
usuário. Essa pendência não invalida a ativação técnica do CI, mas permanece
como limitação de acessibilidade assistiva.

Também permanece pendente:

- publicar a correção em branch dedicada após autorização;
- abrir pull request sem merge automático;
- comprovar todos os jobs verdes no novo commit;
- registrar uma segunda execução real para avaliar cache e variação.
