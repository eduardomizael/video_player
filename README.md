# Video Player/Editor

Aplicativo simples escrito em Python 3.12 que usa `python-vlc` para reprodu\u00e7\u00e3o de v\u00eddeos. Permite adicionar e editar cap\u00edtulos de arquivos MP4.

## Recursos

- Abrir v\u00eddeos e editar cap\u00edtulos
- Cada capítulo pode ter subitens que herdam o tempo do pai
- Aba adicional para editar lista de casting
- Menu para abrir novos arquivos
- Arquivo `config.json` armazena:
  - Intervalo de atualiza\u00e7\u00e3o da interface
  - Tempo dos saltos r\u00e1pidos (curto e longo)
  - Teclas de atalho para play/pause e avan\u00e7o/retrocesso
  - N\u00edvel de volume do player
- Bot\u00f5es de avan\u00e7ar/retroceder
- Controles reorganizados em duas linhas com tempo e barra de progresso na parte superior e bot\u00f5es de reprodu\u00e7\u00e3o na inferior
- Tela de configura\u00e7\u00f5es para definir atalhos (basta pressionar a tecla desejada)

## Instalação

1. Certifique-se de ter o Python 3.12 instalado.
2. Instale a dependência `python-vlc` com `pip install python-vlc`.

## Uso

Execute `python app.py` para iniciar o programa e escolha o vídeo que deseja editar.
