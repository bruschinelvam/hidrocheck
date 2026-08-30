# HidroCheck — Complexo Germano

Versão **v23.5 — upload de HGA por sessão**, criada a partir da `v23_4_INA_PZ_PM_Ativos` sem alteração do
padrão visual aprovado nem das regras de QA/QC e Δ Cota.

## Executar

No Windows, extraia o pacote e abra `ABRIR_HIDROCHECK.bat`.

Execução manual:

```powershell
py -m pip install -r requirements.txt
py -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

## Atualizar a HGA na sessão

1. Abra a área discreta **Atualização da base**.
2. Em **Atualizar base HGA**, selecione uma HGA completa em `.xlsx`, no mesmo
   formato de `HGA-28082026.xlsx`.
3. Aguarde a confirmação **Base carregada com sucesso**.

A planilha enviada substitui a HGA padrão apenas na sessão atual. Ela não é
concatenada ao histórico, não é salva em disco e não altera os arquivos de
`data/`. O botão **Usar base padrão** restaura imediatamente a base incorporada.

Antes da troca, o aplicativo exige `Ponto`, `Natureza do Ponto`,
`Situacao Atual`, `Data`, `Tipo_Dado` e `Cota_NA_m`, além de datas e cotas
utilizáveis. Arquivo incompatível, ilegível ou sem linhas válidas é rejeitado e
o aplicativo continua com a base padrão, sem exibir traceback.

## Metodologia atual

O resultado principal é a comparação direta e auditável:

`Δ Cota = cota atual representativa − cota de referência`

- 12 meses é o período principal; 90 dias é complementar.
- Δ negativo indica tendência de redução da cota.
- Valor próximo de zero indica comportamento estável.
- Δ positivo indica tendência de elevação da cota.
- A classificação da faixa estável usa `±0,10 m`.
- Não há estimativa temporal de valores ausentes nem geração de superfícies.
- Os PTRs são apresentados somente como contexto espacial e operacional.
- Os mapas de variação e de confiabilidade permanecem separados.

Instrumentos automáticos usam a mediana de leituras válidas e consistentes dos
últimos sete dias, com no mínimo três datas de medição. Instrumentos manuais
usam a última medição manual válida. A data de corte é sempre derivada da
leitura válida mais recente do snapshot da base.

## QA/QC público

Os únicos status apresentados são:

- Conforme;
- Acompanhar;
- Revisão recomendada;
- Sem atualização recente.

As verificações automáticas incluem repetição exata prolongada, sinais recentes
distintos do comportamento habitual, mudança de patamar ainda sem confirmação,
oscilação recente e ausência de atualização. Valores manuais exatamente
repetidos são permitidos e não são classificados como repetição automática.

## Escopo operacional

- Complexo Germano, incluindo Setor Norte e Setor Sul;
- `PVirtual` e `COTA-NA-REJEITO` não participam da análise;
- `G00-11PTR006` permanece com o override operacional `Tamponado`;
- a base original permanece preservada em `data/`;
- uma HGA enviada permanece somente na memória da sessão;
- os resultados processados ficam em `out/`.

Consulte `METODOLOGIA_DELTA_COTA_v23.md`, `VALIDACAO_v23.md` e
`VALIDACAO_UPLOAD_v23_5.md` para a descrição auditável e os casos verificados.

## Linguagem para apresentação corporativa

- “INA/PZ/PM sem comparação no período” significa que faltou cota atual representativa
  ou referência adequada; não significa instrumento inválido.
- Resultados, mapas, rankings de redução/elevação e avaliação técnica incluem
  INAs, piezômetros (PZs) e poços de monitoramento (PMs).
- O traço `—` em Δ Cota significa comparação não calculada, nunca valor zero.
- Situações como possível travamento, possível outlier, mudança ainda sem
  confirmação e oscilação recente são apresentadas com significado e ação
  recomendada em linguagem direta.
- A indicação técnica de origem da situação cadastral não é exibida na interface.
- A página inicial é `Avaliação técnica` e apresenta, na mesma linha, último
  valor, data, Δ Cota, situação explicada e ação recomendada.
- As sínteses executivas apresentam exclusivamente instrumentos com situação
  operacional `Ativo` e ao menos uma leitura válida no ano da data de corte.
- Resultados, rebaixamento, mapas, rankings e avaliação técnica incluem INAs,
  piezômetros (PZs) e poços de monitoramento (PMs).
- PTRs permanecem somente como contexto espacial e não entram no Δ Cota.
- Um valor desatualizado permanece visível como histórico, acompanhado do número
  de dias desde a leitura e da explicação de por que não entrou no Δ Cota.

Ferramenta de apoio à análise técnica. Os resultados devem ser interpretados
em conjunto com as informações disponíveis e o contexto operacional.
