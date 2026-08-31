# Validação — HidroCheck v23.6 Home/Índice

## Escopo da rodada

A v23.6 foi criada como cópia separada da v23.5. As alterações foram limitadas
à Home/Índice, ao cabeçalho, à navegação horizontal e ao posicionamento visual
da utilidade de upload HGA.

## Testes automatizados

- Compilação de `streamlit_app.py`, `src/delta_cota.py` e `src/hga_upload.py`:
  concluída sem erro.
- Suíte completa: **30 testes executados; 30 aprovados**.
- Casos cobertos: Δ Cota, QA/QC automático e manual, data de corte, casos reais,
  fallback da HGA, arquivo inválido, upload válido e alteração dos resultados
  quando a HGA muda.

## Navegação e interface

Validação no navegador local:

- abertura inicial na Home/Índice;
- Home → Resultados → Início;
- Home → Avaliação técnica → Início;
- Home → Explorar instrumento → Início;
- Home → Confiabilidade dos dados → Início;
- Home → Metodologia → Início;
- item interno ativo identificado por linha inferior;
- estado da página preservado pelo `session_state`, sem navegação externa.

Em **1366 × 768**, a Home inteira permaneceu visível sem rolagem. Em
**1024 × 700**, a composição continuou legível; a navegação pode quebrar a
última opção para uma segunda linha e a Home pode exigir uma rolagem vertical
curta, o que é a limitação responsiva observada.

## Upload HGA

O arquivo local `data/HGA-28082026.xlsx` (17,2 MB) foi enviado pela nova
utilidade **Atualizar base**. Foram confirmados:

- validação e processamento integral do arquivo;
- mensagem de sucesso com dados até 27/08/2026;
- carregamento da página Resultados com a base ativa na sessão;
- funcionamento de **Usar base padrão** e restauração da base incorporada.

O upload continua usando as mesmas chaves de sessão, validações, processamento
e fallback da v23.5; somente o contêiner visual mudou de expander para popover.

## Integridade funcional

Comparação SHA-256 com a v23.5 confirmou identidade dos **15 arquivos** de
`src/`, `data/`, `out/`, `config/`, `assets/` e dos documentos técnicos de
metodologia/validação. Uma comparação estrutural das funções do app verificou
31 funções existentes: somente `brand_header` mudou, por apresentação; quatro
helpers exclusivamente de interface foram adicionados e nenhuma função foi
removida.

**Conclusão:** nenhuma metodologia, fonte de dados, regra de cálculo, QA/QC ou
lógica funcional foi alterada na v23.6.
