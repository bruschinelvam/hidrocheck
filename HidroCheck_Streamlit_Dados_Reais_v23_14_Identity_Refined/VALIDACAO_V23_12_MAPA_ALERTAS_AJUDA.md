# Validação — HidroCheck v23.12 Mapas, alertas e ajuda

## Escopo visual

- símbolo especial de condicionante removido dos mapas;
- item de legenda dos instrumentos sem comparação ocultado;
- legenda do mapa de Δ Cota mantida apenas com INA/PZ/PM e PTR;
- alerta institucional confirmado para 0027-INA-155 e 0027-INA-156;
- ajuda contextual ampliada de forma seletiva, sem novos blocos explicativos.

## Integridade e funcionamento

- 30/30 testes automatizados aprovados;
- 155 e 156 exibidos como “Alerta · redução de cota” na base atual;
- ajudas de cota atual, referência e Δ Cota confirmadas no explorador;
- upload HGA e fallback cobertos pela suíte existente;
- arquivos de dados, metodologia, cálculos, QA/QC, configuração e assets idênticos aos da v23.11.

Os alertas de condicionantes são uma camada de apresentação institucional. Eles
não substituem, forçam nem alteram o status técnico de QA/QC ou os cálculos.
