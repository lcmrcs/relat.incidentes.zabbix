# Política de Baselines Visuais

As baselines protegem a identidade visual do relatório contra alterações
acidentais. Todas usam datas, hosts, unidades e eventos fictícios.

## Regras de aprovação

1. O CI nunca cria nem atualiza baselines.
2. A atualização local exige o argumento `--update-baselines`.
3. Toda imagem alterada deve ser revisada nos modos solar e lunar.
4. A pull request deve explicar por que a aparência mudou.
5. Imagens em `artifacts/visual-accessibility/diffs/` devem ser conferidas antes
   da aprovação.
6. Uma baseline não pode ser atualizada apenas para esconder corte, overflow,
   contraste inadequado ou outro erro.
7. Nenhuma captura pode conter host, unidade, IP, URL ou evento operacional.

## Executar e revisar

Comparar sem alterar referências:

```bash
python scripts/validate_visual_accessibility.py --visual-only
```

Revisar lado a lado:

```text
artifacts/visual-accessibility/current/
zabbix-report/tests/visual_baselines/
artifacts/visual-accessibility/diffs/
```

Somente após aprovação visual explícita:

```bash
python scripts/validate_visual_accessibility.py --visual-only --update-baselines
python scripts/validate_visual_accessibility.py --visual-only
```

Restaurar baselines ainda não commitadas:

```bash
git restore --source=HEAD -- zabbix-report/tests/visual_baselines
```

Confirmar que as imagens e evidências não introduziram dados sensíveis:

```bash
python scripts/check_secrets.py
git diff --stat
git diff -- zabbix-report/tests/visual_baselines
```

Arquivos PNG não possuem diff textual útil. A revisão deve usar as imagens
atuais, esperadas e de diferença geradas pela suíte.

## Mudança de navegador

A evidência JSON registra navegador, versão, sistema, tema e resolução. Uma
atualização do Edge pode alterar rasterização de fontes ou pixels sem mudar o
CSS. Quando isso ocorrer:

1. confirme a versão indicada no artefato;
2. reproduza localmente no mesmo sistema;
3. diferencie alteração de renderização de um erro real de layout;
4. revise todas as imagens afetadas;
5. atualize referências somente depois dessa análise.

O runner `windows-latest` recebe atualizações periódicas do Edge. O navegador
não é atualizado nem baixado pelos workflows do projeto.
