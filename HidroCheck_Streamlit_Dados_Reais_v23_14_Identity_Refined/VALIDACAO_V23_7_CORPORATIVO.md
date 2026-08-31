# Validação — HidroCheck v23.7 Corporativo Compacto

## Escopo

A v23.7 foi criada como cópia separada da v23.6. As alterações se limitam à
densidade visual, aos textos da interface, aos indicadores e à seleção de
colunas das tabelas exibidas.

## Verificações

- **30/30 testes automatizados aprovados**;
- abertura inicial na Home sem exceções;
- Home → cada uma das cinco páginas → Home, sem exceções, pelo testador nativo
  do Streamlit;
- navegação horizontal e cinco destinos confirmados;
- **12/12 arquivos protegidos** de dados, cálculos, configuração, resultados e
  assets idênticos aos da v23.6;
- compilação do aplicativo aprovada;
- regras responsivas mantidas para notebook e janela reduzida.

O upload continua coberto pelos oito testes específicos de arquivo válido,
arquivo incompatível, fallback, atualização da data de corte e alteração dos
resultados. O fluxo e o processamento são os mesmos da v23.6; somente o texto
do popover foi reduzido.

## Integridade funcional

Não foram alterados dados, metodologia, cálculos de Δ Cota, regras de QA/QC,
validações do upload, estado da sessão, fallback ou processamento da HGA.

## Limitação do ambiente de validação

A inspeção visual final nas janelas de 1366 × 768 e 1024 × 700 não pôde ser
repetida porque o navegador de teste bloqueou o acesso ao endereço local. Essas
duas dimensões já haviam sido verificadas na v23.6; a v23.7 preserva os mesmos
breakpoints e reduz conteúdo, alturas e largura mínima das tabelas. A navegação
e a renderização das páginas foram verificadas pelo testador nativo do
Streamlit, sem exceções.
