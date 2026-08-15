# Video Player/Editor

Aplicativo simples escrito em Python 3.12 que usa `python-vlc` para reprodução de vídeos. Permite adicionar e editar capítulos de arquivos MP4.

## Recursos

- Abrir vídeos e editar capítulos
- Cada capítulo pode ter subitens que herdam o tempo do pai
- Editor de Legendas padrão `.srt` com tempo estendido (milissegundos) e exibição nativa em tempo real no player VLC
- Aba adicional para editar lista de casting
- Menu para abrir novos arquivos
- Arquivo `config.json` armazena:
  - Intervalo de atualização da interface
  - Tempo dos saltos rápidos (curto e longo)
  - Teclas de atalho para play/pause e avanço/retrocesso
  - Nível de volume do player
- Botões de avançar/retroceder
- Controles reorganizados em duas linhas com tempo e barra de progresso na parte superior e botões de reprodução na inferior
- Tela de configurações para definir atalhos (basta pressionar a tecla desejada)

## Instalação

1. Certifique-se de ter o Python 3.12 instalado.
2. Instale a dependência `python-vlc` com `pip install python-vlc`.

## Uso

Execute `python app.py` (ou `uv run python app.py`) para iniciar o programa e escolha o vídeo que deseja editar.

## Gerando Executável (.exe)

Para gerar uma versão executável standalone no Windows:

- **Via terminal**: Execute `uv run python build.py` ou `python build.py`.
- **Via clique duplo**: Clique duas vezes no arquivo [`build.bat`](file:///c:/Users/eduar/Desktop/chapter_editor/build.bat).

O executável final será gerado dentro do diretório `dist/EditorDeCapitulos.exe`.

