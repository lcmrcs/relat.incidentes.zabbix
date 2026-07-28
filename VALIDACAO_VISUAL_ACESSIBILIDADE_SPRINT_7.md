# Validação Visual e de Acessibilidade — Sprint 7

- Data: 2026-07-28T10:56:37-03:00
- Navegador: Microsoft Edge 150.0.4078.99
- Sistema: Windows 11 / WSL (6.18.33.1-microsoft-standard-WSL2)
- Dados: exclusivamente fictícios e sanitizados.
- Tolerância visual: 0.35% dos pixels.

## Regressão visual

| Tela | Tema | Resolução | Diferença | Resultado |
| --- | --- | --- | ---: | --- |
| desktop_solar_cabecalho | solar | 1600x1000 | 0.0000% | Aprovado |
| desktop_lunar_inteligencia | lunar | 1600x1000 | 0.0000% | Aprovado |
| desktop_solar_rankings | solar | 1600x1000 | 0.0000% | Aprovado |
| tablet_solar_criticidade | solar | 768x1024 | 0.0000% | Aprovado |
| tablet_lunar_filtros | lunar | 768x1024 | 0.0000% | Aprovado |
| mobile_solar_tabela | solar | 390x844 | 0.0000% | Aprovado |
| mobile_lunar_incidente | lunar | 390x844 | 0.0000% | Aprovado |
| desktop_solar_zabbix | solar | 1600x1000 | 0.0000% | Aprovado |
| desktop_lunar_confea | lunar | 1600x1000 | 0.0000% | Aprovado |
| mobile_solar_vazio | solar | 390x844 | 0.0000% | Aprovado |
| desktop_lunar_grande_volume | lunar | 1600x1000 | 0.0000% | Aprovado |

## Acessibilidade e responsividade

| Cenário | Viewport | Zoom | Violações críticas/sérias | Resultado |
| --- | --- | ---: | ---: | --- |
| mobile_solar | 390x844 | 100% | 0 | Aprovado |
| mobile_lunar | 390x844 | 100% | 0 | Aprovado |
| tablet_solar | 768x1024 | 100% | 0 | Aprovado |
| tablet_lunar | 768x1024 | 100% | 0 | Aprovado |
| desktop_solar | 1600x1000 | 200% | 0 | Aprovado |
| desktop_lunar | 1600x1000 | 200% | 0 | Aprovado |

Baselines nunca são alteradas durante a validação comum. Para aprovar
mudanças revisadas, execute explicitamente:

```bash
python scripts/validate_visual_accessibility.py --update-baselines
```

Diferenças reprovadas ficam em `artifacts/visual-accessibility/diffs/`.
