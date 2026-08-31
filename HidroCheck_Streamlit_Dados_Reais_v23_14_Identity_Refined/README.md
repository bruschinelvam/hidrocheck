# HidroCheck — Complexo Germano

Versão **v23.12 — Mapas, alertas e ajuda**, criada como cópia separada da v23.11.
Esta rodada aprimora somente a apresentação e a priorização institucional.
Dados, metodologia, cálculos, QA/QC, validações e processamento da HGA permanecem inalterados.

## Interface

- Home em formato de índice, com cinco acessos diretos;
- nova fotografia local do Complexo Germano na capa;
- enquadramento superior, sem grade e sem mira sobre a fotografia;
- filtro reduzido para preservar céu, relevo e cores da imagem;
- ajuda contextual nativa ao lado dos termos técnicos que exigem explicação;
- explicação de Δ Cota com fórmula, exemplo e interpretação dos sinais;
- faixas de cor padronizadas nos indicadores Abaixo, Estável e Acima;
- seção permanente para os condicionantes ICMBio 0027-INA-155 e 0027-INA-156;
- alerta institucional no explorador para todos os instrumentos condicionantes;
- legenda do mapa de Δ Cota reduzida aos símbolos de INA/PZ/PM e PTR;
- ajuda contextual ampliada para cota atual, referência e estados de QA/QC;
- navegação interna horizontal e compacta;
- mapa mantido como elemento principal de Resultados;
- indicadores organizados em faixa reta, sem cards volumosos;
- tabelas principais com colunas objetivas;
- detalhes técnicos disponíveis em expansores;
- atualização da HGA mantida como utilidade discreta.

## Executar

No Windows, extraia o pacote e abra `ABRIR_HIDROCHECK.bat`.

Execução manual:

```powershell
py -m pip install -r requirements.txt
py -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

## Atualizar a HGA

1. Abra **Atualizar base** na Home ou na barra interna.
2. Selecione uma HGA completa em `.xlsx` no padrão da base incorporada.
3. Aguarde a confirmação do carregamento.

A planilha vale apenas na sessão atual, não é salva nem concatenada ao
histórico. Arquivos incompatíveis são rejeitados e a base padrão permanece
ativa. **Usar base padrão** restaura a base incorporada.

## Metodologia preservada

`Δ Cota = cota atual representativa − cota de referência`

- períodos de 12 meses e 90 dias;
- faixa estável de `±0,10 m`;
- sem estimativa de valores ausentes ou geração de superfícies;
- PTRs somente como contexto espacial e operacional;
- mapas de variação e confiabilidade separados;
- automáticos: mediana recente válida e consistente;
- manuais: última medição manual válida;
- data de corte derivada do snapshot da base.

Os status públicos de QA/QC permanecem **Conforme**, **Acompanhar**,
**Revisão recomendada** e **Sem atualização recente**.

Consulte `METODOLOGIA_DELTA_COTA_v23.md`, `VALIDACAO_v23.md`,
`VALIDACAO_UPLOAD_v23_5.md` e `VALIDACAO_V23_12_MAPA_ALERTAS_AJUDA.md` para os critérios
e verificações.
