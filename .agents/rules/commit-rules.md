# Regras de Commits para o Agente

## Diretrizes Obrigatórias para Commits no Git

1. **Autorização Expressa**:
   - **NUNCA** faça commits automaticamente ou por iniciativa própria.
   - Execute o comando `git commit` **apenas** quando o usuário solicitar ou autorizar expressamente.

2. **Commits Semânticos em Português**:
   - As mensagens de commit devem obrigatoriamente utilizar o padrão de **Commits Semânticos** em Português do Brasil.
   - Prefixos recomendados:
     - `feat:` para novas funcionalidades
     - `fix:` para correção de bugs
     - `refactor:` para refatoração de código sem alterar comportamento
     - `test:` para adição ou modificação de testes
     - `docs:` para alterações em documentação
     - `chore:` para tarefas de manutenção, configurações ou build

3. **Mensagens Claras e Diretas**:
   - As mensagens devem ser objetivas, precisas e direto ao ponto.
   - **PROIBIDO** mensagens vagas ou genéricas (ex: "ajustes no código", "melhorias gerais", "atualiza arquivos").
   - Exemplo correto: `feat(app): adiciona verificação de instalação do VLC antes da inicialização`

4. **Granularidade e Agrupamento Lógico**:
   - Respeite o histórico de alterações agrupando apenas mudanças que sejam pertinentes ao mesmo escopo.
   - **EVITE** commits gigantescos ou únicos contendo alterações não relacionadas.
   - Quebre as alterações em commits menores, atômicos e focados sempre que apropriado.
