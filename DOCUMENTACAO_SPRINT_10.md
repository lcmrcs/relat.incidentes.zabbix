# Sprint 10 — Compatibilidade temporal

## Modelo canônico

- Unix timestamps e cálculos de duração usam UTC internamente.
- Conversões anteriores a 1970 são feitas por diferença em relação ao epoch,
  sem depender de `datetime.timestamp()` ou `datetime.fromtimestamp()`.
- Datetimes com fuso são convertidos para UTC.
- Datetimes sem fuso representam o horário operacional do relatório.
- A apresentação permanece em `DD/MM/AAAA HH:MM`, no horário explícito de
  Brasília (`UTC-03:00`), independentemente do fuso do computador.

O módulo `zabbix-report/time_utils.py` concentra somente parsing, conversão,
formatação e relógios necessários. Duração, idade do passivo, recuperação,
recorrência e integridade continuam com as regras consolidadas.

## Cobertura

Os testes usam exclusivamente dados fictícios e cobrem epoch negativo, zero,
datas antes e depois de 1970, limites de calendário, ano bissexto, datetimes
com e sem fuso e alteração do timezone do processo. O workflow
`Compatibilidade temporal` executa o mesmo conjunto focal em Linux e Windows.

## Comandos

WSL/Linux:

```bash
python -m pytest \
  zabbix-report/tests/test_time_utils.py \
  zabbix-report/tests/test_incident_model.py \
  zabbix-report/tests/test_data_integrity.py \
  zabbix-report/tests/test_summary.py
```

Windows:

```powershell
python -m pytest zabbix-report/tests/test_time_utils.py zabbix-report/tests/test_incident_model.py zabbix-report/tests/test_data_integrity.py zabbix-report/tests/test_summary.py
```
