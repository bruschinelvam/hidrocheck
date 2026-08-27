# HidroCheck — dados reais

**Transformando dados em valor: Resultados da operação do sistema de rebaixamento**

Aplicação Streamlit com os dados reais fornecidos para o projeto aplicativo. O app executa QA/QC da rede de monitoramento hidrogeológico, mostra a saúde dos instrumentos, permite consulta individual e apresenta o módulo de resultados do rebaixamento.

## Arquivo principal

`streamlit_app.py`

## Rodar localmente

```powershell
py -m pip install -r requirements.txt
py -m streamlit run streamlit_app.py
```

## Publicar no Streamlit Community Cloud

1. Crie um repositório no GitHub.
2. Envie **todo o conteúdo desta pasta**, preservando `data/`, `src/`, `out/`, `assets/` e `.streamlit/`.
3. No Streamlit Community Cloud, crie um app apontando para:
   - branch: `main`
   - main file: `streamlit_app.py`
4. Use Python 3.12 no deploy.
5. Publique e teste o link gerado.

## Atenção

Esta versão contém a base real incluída no pacote. Se o app/repositório forem públicos, os dados poderão ficar acessíveis fora da Samarco. Use visibilidade e hospedagem compatíveis com a autorização recebida.
