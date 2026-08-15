# Video Player/Editor

Aplicativo simples escrito em Python 3.12 que usa `python-vlc` para reprodução de vídeos. Permite adicionar e editar capítulos de arquivos MP4.

## Recursos

- Abrir vídeos e editar capítulos
- Capítulos e subcapítulos podem ter níveis hierárquicos ilimitados
- O botão de capítulo cria um irmão do item selecionado; o botão de subcapítulo cria um filho direto
- Irmãos são ordenados pelo início e podem se sobrepor livremente
- O fim dos capítulos pais é ampliado automaticamente quando um descendente termina depois deles
- Editor de Legendas padrão `.srt` com tempo estendido (milissegundos) e exibição nativa em tempo real no player VLC
- Aba adicional para editar lista de casting
- Aba de metadados em árvore, com chave e valor; somente folhas podem ter valor e, ao criar um filho, o valor do pai é transferido para ele
- Menu para abrir novos arquivos
- Arquivo `config.json`, mantido ao lado do `app.py` ou do executável, armazena:
  - Intervalo de atualização da interface
  - Tempo dos saltos rápidos (curto e longo)
  - Teclas de atalho para play/pause e avanço/retrocesso
  - Nível de volume do player
- Botões de avançar/retroceder
- Roda do mouse sobre a barra de progresso para saltos longos
- Controles reorganizados em duas linhas com tempo e barra de progresso na parte superior e botões de reprodução na inferior
- Ações de adicionar e remover posicionadas no topo dos painéis, com seleção automática do item recém-criado
- Tela de configurações para definir atalhos (basta pressionar a tecla desejada)
- Validação dos intervalos de capítulos, subcapítulos e legendas antes do salvamento
- Salvamento atômico dos arquivos, com cópia `.bak` dos capítulos e legendas anteriores
- Preservação de configurações corrompidas em um arquivo `.corrompido_*.bak` antes de restaurar os padrões

## Instalação

1. Certifique-se de ter o Python 3.12 instalado.
2. Instale as dependências com `uv sync --dev`.

## Uso

Execute `python app.py` (ou `uv run python app.py`) para iniciar o programa e escolha o vídeo que deseja editar.

O `config.json` é resolvido pelo local da aplicação, independentemente do diretório em que o comando foi executado. No
modo fonte ele fica ao lado de `app.py`; no executável ele fica ao lado de `EditorDeCapitulos.exe`.

## Gerando Executável (.exe)

Para gerar uma versão executável standalone no Windows:

- **Via terminal**: Execute `uv run python build.py` ou `python build.py`.
- **Via clique duplo**: Clique duas vezes no arquivo [`build.bat`](file:///c:/Users/eduar/Desktop/chapter_editor/build.bat).

O executável final será gerado dentro do diretório `dist/EditorDeCapitulos.exe`.

