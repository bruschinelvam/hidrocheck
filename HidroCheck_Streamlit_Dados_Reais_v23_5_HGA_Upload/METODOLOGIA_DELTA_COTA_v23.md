# Metodologia Δ Cota — HidroCheck v23

## Princípio

O HidroCheck acompanha a variação temporal da cota do nível d'água a partir da
comparação entre valores representativos de diferentes períodos:

`Δ Cota = cota atual representativa − cota de referência`

O período principal é 12 meses e o período complementar é 90 dias. Cada
período possui resultado próprio e não compartilha a mesma escala cartográfica.
Δ negativo representa tendência de redução da cota, resultado entre `−0,10 m`
e `+0,10 m` representa comportamento estável e Δ positivo representa tendência
de elevação da cota. O resultado descreve o comportamento observado e não
estabelece diagnóstico causal.

## Snapshot e pré-processamento

A data de corte é a data mais recente com leitura válida no universo analisado.
O relógio do computador não participa do cálculo. Registros posteriores a essa
data não definem a condição atual.

Somente `Cota_NA_m` válida participa dos cálculos. Duplicatas idênticas na mesma
data e hora são consolidadas. Cotas divergentes na mesma data e hora são
tratadas como conflito temporal: os registros conflitantes não entram na cota
representativa e, quando recentes, o ponto recebe status `Acompanhar`.

## Modo de monitoramento

O modo é definido pela aquisição operacional recente do instrumento. Um INA, PZ ou PM
com aquisição automática recente permanece classificado como automático mesmo
quando há medições manuais de apoio ou QA/QC na série. Essas medições manuais
continuam visíveis no histórico, mas não compõem a mediana automática.

## Cota representativa atual

Para instrumentos automáticos, são usadas leituras automáticas válidas dos
últimos sete dias em relação à data de corte, após as verificações de QA/QC. A
cota atual é a mediana de pelo menos três datas de medição válidas e
consistentes.

Para instrumentos manuais, a cota atual é a última medição manual válida.
Repetições exatas em campanhas manuais são permitidas e não caracterizam, por
si só, repetição automática prolongada.

## Referências

Para instrumentos manuais, a referência é a medição válida mais próxima da
data-alvo, com tolerância máxima de `±30 dias`.

Para instrumentos automáticos, a referência é a mediana de um trecho curto e
consistente próximo da data-alvo, com tolerância máxima de `±14 dias` e no
mínimo três datas de medição. Não são estimados valores ausentes. Sem referência
adequada, o instrumento permanece visível no mapa com apresentação neutra e
sem Δ válido para o período.

## QA/QC automático

- Repetição prolongada: mesmo valor armazenado em pelo menos cinco datas
  consecutivas. Enquanto persiste, não há cota atual representativa. Após o
  término, são exigidas três novas leituras coerentes e não idênticas.
- Leitura isolada: identificada de forma adaptativa a partir das diferenças e
  da dispersão robusta do histórico do próprio instrumento. Se não houver
  confirmação posterior suficiente, o status é `Acompanhar` e a nova condição
  não é usada como representativa.
- Mudança sustentada: sequência progressiva e coerente é preservada e não muda
  o QA/QC somente por sua magnitude.
- Mudança de patamar: a condição inicial recebe `Acompanhar`; o novo patamar
  passa a ser representativo após três leituras posteriores coerentes.
- Oscilação: compara o comportamento recente com o histórico, combinando
  aumento relativo, magnitude absoluta e persistência de sobe/desce depois de
  considerar o comportamento direcional. Sequência monotônica não é tratada
  como oscilação.
- Atualização: instrumentos automáticos com cadência diária recebem `Sem
  atualização recente` após mais de cinco dias sem nova leitura. Instrumentos
  manuais usam tolerância baseada na cadência observada de campanhas.

Os status públicos são somente `Conforme`, `Acompanhar`, `Revisão recomendada`
e `Sem atualização recente`.

## Apresentação espacial

O mapa de variação mostra somente pontos sobre a imagem aérea. INAs, PZs e PMs com cota
atual e referência válidas recebem a cor contínua de Δ Cota; os demais
permanecem visíveis em cinza. PTRs usam símbolo separado e nunca participam da
escala de Δ. O mapa de confiabilidade é independente e apresenta os status de
QA/QC.

As informações espaciais e operacionais são apresentadas como apoio à avaliação
técnica. Proximidade de PTR e comportamento da vizinhança são contextos, não
declarações de causalidade.
