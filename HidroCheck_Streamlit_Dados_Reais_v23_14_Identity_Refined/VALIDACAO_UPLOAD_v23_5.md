# Validação do upload HGA — v23.5

## Comportamento coberto

- upload `.xlsx` válido no padrão HGA;
- rejeição de arquivo sem coluna obrigatória;
- rejeição de arquivo corrompido ou ilegível;
- rejeição de base sem linhas válidas de data e cota;
- fallback para a base padrão, inclusive diante de erro de processamento;
- data de corte derivada da última leitura válida da base carregada;
- alteração dos resultados de Δ Cota quando as cotas da HGA mudam;
- manutenção da HGA ativa em `st.session_state` durante a sessão;
- retorno explícito para a base incorporada.

## Resultado automatizado

Foram executados os 22 testes originais da v23.4 e 8 testes específicos do
upload. Resultado: **30 testes aprovados**.

## Prova com a HGA real

O arquivo completo `HGA-28082026.xlsx`, com 245.685 linhas de dados, foi
carregado pelo novo caminho em memória. O processamento retornou:

- data de corte: **27/08/2026**;
- 141 instrumentos diagnosticados;
- 19 eventos de QA/QC;
- 88 comparações válidas de 12 meses.

Esses totais são compatíveis com a base e os resultados incorporados à v23.4.
Nenhum arquivo enviado é persistido pelo recurso de upload.
