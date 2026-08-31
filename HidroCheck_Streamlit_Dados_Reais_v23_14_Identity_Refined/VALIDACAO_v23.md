# Validação — HidroCheck v23

## Verificações automatizadas

A suíte contém testes sintéticos e de integração com os resultados reais da
HGA. Na validação final, **22 testes passaram**. A aplicação também foi aberta
por teste automatizado em cada uma das cinco páginas, sem exceções. A suíte
verifica:

- instrumento automático em condição regular;
- repetição automática prolongada;
- repetição encerrada sem três leituras de confirmação;
- leitura isolada e retorno ao regime anterior;
- mudança sustentada coerente de vários metros;
- mudança de patamar ainda sem confirmação e patamar confirmado;
- aumento de oscilação;
- automático sem atualização recente;
- manual com valores exatamente repetidos;
- ausência de referência válida de 12 meses ou 90 dias;
- conflito temporal;
- classificação do modo atual de monitoramento;
- permanência visual, em cinza, do instrumento sem Δ válido;
- PTR sem participação na escala de Δ.
- explicação pública do significado de comparação não calculada;
- descrições didáticas de possível travamento, possível outlier, mudança sem
  confirmação e oscilação recente;
- ausência da indicação técnica de origem cadastral na interface.
- `Avaliação técnica` como página inicial;
- exibição do último valor e da data mesmo quando a leitura é histórica;
- explicação do número de dias sem leitura e ação específica para monitoramento
  automático, manual ou somente histórico.
- restrição da síntese `Situação dos instrumentos ativos` aos instrumentos cuja
  situação operacional é `Ativo`.
- restrição de `Itens ativos para acompanhamento e revisão` aos instrumentos
  ativos, inclusive na opção `Mostrar todos`.
- exigência de pelo menos uma leitura válida no ano da data de corte para as
  sínteses de instrumentos ativos;
- inclusão conjunta de 96 INAs, 5 PZs e 20 PMs na análise de nível d’água;
- confirmação de 88 comparações válidas de 12 meses entre esses 121 instrumentos;
- permanência dos PTRs apenas como contexto espacial, fora da escala de Δ Cota.

## Casos reais conferidos

O processamento integral de `HGA-28082026.xlsx` derivou `27/08/2026` como data
de corte válida. O resultado reuniu 108 pontos `Conforme`, 19 em `Acompanhar` e
14 `Sem atualização recente`.

| Instrumento | Comportamento conferido | Resultado esperado |
|---|---|---|
| 0027-INA-018 | Automático regular | Conforme |
| 0027-INA-054 | Repetição exata prolongada | Acompanhar; sem cota representativa |
| 0027-INA-034 | Repetição encerrada recentemente | Acompanhar; confirmação ainda insuficiente |
| 0027-INA-107 | Leitura isolada | Acompanhar; leitura isolada não redefine a condição |
| 0029-INA-097 | Redução sustentada e coerente | Conforme; redução preservada |
| 30LI008 | Mudança abrupta recente | Acompanhar; confirmação ainda insuficiente |
| 0028-INA-086 | Novo patamar coerente | Condição representativa após confirmação |
| 0028-INA-137 | Oscilação recente maior | Acompanhar |
| 0029-INA-133 | Automático sem atualização | Sem atualização recente |
| 0027-INA-130 | Manual com cotas repetidas | Conforme; não tratado como repetição automática |
| 0027-INA-073 | Instrumento manual | Última medição manual válida preservada |

## Pontos para validação técnica humana

1. Confirmar que a data de corte derivada da HGA corresponde ao fechamento
   operacional esperado para o snapshot.
2. Confirmar a faixa institucional de comportamento estável adotada na versão:
   `±0,10 m`.
3. Revisar periodicamente a sensibilidade dos limites adaptativos de leitura
   isolada, mudança de patamar e oscilação quando novos snapshots forem
   incorporados.

Ferramenta de apoio à análise técnica. Os resultados devem ser interpretados em
conjunto com as informações disponíveis e o contexto operacional.
