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
- Aba de imagens: recorte por posicionamento e zoom, abertura de arquivo ou colagem da área de transferência e associação de imagens a capítulos, elenco ou metadados
- Arquivo `.chp` (SQLite) por vídeo para capítulos, elenco, metadados e imagens; imagens são armazenadas como dados binários recortados, sem manter o original
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
- Salvamento atômico das legendas, com cópia `.bak` da versão anterior; os dados `.chp` são gravados em transações SQLite
- Preservação de configurações corrompidas em um arquivo `.corrompido_*.bak` antes de restaurar os padrões

## Instalação

1. Certifique-se de ter o Python 3.12 instalado.
2. Instale as dependências com `uv sync --dev`.

## Uso

Execute `python app.py` (ou `uv run python app.py`) para iniciar o programa e escolha o vídeo que deseja editar.

Ao salvar informações de um vídeo, o aplicativo cria um arquivo `.chp` ao lado dele. Esse arquivo é SQLite e substitui o uso padrão do JSON. Arquivos JSON existentes não são convertidos automaticamente nesta versão.

O `config.json` é resolvido pelo local da aplicação, independentemente do diretório em que o comando foi executado. No
modo fonte ele fica ao lado de `app.py`; no executável ele fica ao lado de `EditorDeCapitulos.exe`.

## Interface alternativa em webview

A interface webview é uma segunda entrada desktop, com visual independente. A interface clássica continua sendo
iniciada por `uv run python app.py`, usa Tkinter/VLC e não exige a instalação do pywebview.

Para instalar e abrir a nova interface:

```powershell
uv sync --extra webview --dev
uv run --extra webview python web_app.py
```

Também é possível informar o vídeo ao iniciar:

```powershell
uv run --extra webview python web_app.py "C:\Videos\meu video.mp4"
```

No Windows, a nova interface usa o **Microsoft Edge WebView2 Runtime**. Se ele estiver ausente, instale-o a partir
do [site oficial da Microsoft](https://developer.microsoft.com/microsoft-edge/webview2/). A interface web não precisa
do VLC. Linux e macOS usam os motores disponíveis no pywebview e exigem suas respectivas dependências nativas;
consulte a [instalação do pywebview](https://pywebview.flowrl.com/guide/installation.html). A validação desta versão
foi feita no Windows com WebView2; não há validação de execução ou distribuição em Linux/macOS.

### Recursos da interface web

- Reprodução HTML5 com pausa, saltos, volume, silenciamento, tela cheia e linha do tempo proporcional. Subcapítulos
  são desenhados por cima dos pais, na mesma faixa. Capítulos principais simultâneos usam faixas diferentes;
  capítulos sem sobreposição temporal podem compartilhar a faixa. Há rolagem vertical para projetos maiores.
- Atalhos e intervalos de salto lidos do `config.json`; os atalhos não interferem na digitação dos formulários.
- Capítulos e subcapítulos, com irmãos ordenados pelo início e expansão automática do fim dos ancestrais.
- Edição e exibição das legendas `.srt`, com precisão de milissegundos. O texto é exibido literalmente, sem interpretar HTML.
- Edição de elenco e metadados hierárquicos; ao criar um filho, o valor do metadado pai é transferido à folha.
- Importação de imagens por arquivo ou colagem (`Ctrl+V` no formulário de nova imagem), recorte com proporção,
  zoom e posição, descrição e associação aos capítulos, elenco e metadados.
- Busca nos registros, confirmação de exclusão e proteção contra fechar uma edição com alterações não confirmadas.

Selecione um registro e use **Editar**, ou dê duplo clique para abrir seu formulário. Em capítulos, **＋ Capítulo**
cria um irmão do selecionado; sem seleção, cria um capítulo na raiz. O título é preenchido com **Capítulo N** ou
**Subcapítulo N**, usando o primeiro número disponível entre os irmãos, e fica selecionado para substituição rápida.
A seta ao lado de **＋ Capítulo** abre **Criar capítulo** e **Criar subcapítulo**; a segunda opção exige a seleção
de um capítulo pai. Cada capítulo também possui um botão **⋯**, sempre visível, com **Editar**, **Excluir** e
**Criar subcapítulo**. Os menus aceitam navegação por setas e fechamento com Escape ou clique fora deles.
Nos formulários de capítulos e subcapítulos, os campos de início e fim possuem máscara **hh:mm:ss**: basta digitar
os números (`1234` vira `00:12:34`). Também é possível colar um horário formatado, selecionar e substituir apenas
um componente ou usar **Tempo atual**. Minutos e segundos fora do intervalo de 00 a 59 impedem o salvamento.
Na linha do tempo, a posição representa o início e a largura representa a duração. Os descendentes ficam em camadas
por cima das barras dos pais, com tons diferentes para identificar os níveis. Capítulos principais cujos intervalos
coincidem são separados verticalmente; os demais reutilizam uma faixa livre. O clique em uma barra navega até seu início.
Nos metadados, **Novo** cria um item na raiz
e **Filho** adiciona um descendente. As alterações são gravadas ao confirmar o formulário; não existe gravação
automática de rascunhos. O volume alterado na interface web vale para a sessão atual. A configuração compartilhada
é lida sem ser sobrescrita pela nova interface; sua edição continua disponível na interface clássica.

### Compatibilidade e arquivos locais

As duas interfaces usam `ChapterManager` e `SubtitleManager`, em `logic.py`, para validar e gravar os mesmos
arquivos `.chp` e `.srt`. A nova interface preserva as outras seções ao salvar apenas uma delas. Se detectar uma
alteração externa no arquivo que vai salvar, interrompe a gravação e pede que o vídeo seja reaberto. **Evite editar
o mesmo projeto nas duas interfaces ao mesmo tempo:** a interface clássica não possui essa proteção de conflito.

Os vídeos permanecem no computador, sem conversão ou upload. Um servidor temporário vinculado a `127.0.0.1`, em
porta dinâmica e com caminho aleatório por execução, entrega os arquivos da interface e apenas o vídeo selecionado.
Ele aceita intervalos de bytes para permitir navegação em vídeos grandes e é encerrado junto com a janela.

O suporte à reprodução depende do contêiner, dos codecs e do motor web do sistema. **MP4 (H.264/AAC) e WebM
(VP9/Opus) foram verificados com amostras sintéticas no WebView2.** A extensão `.mp4`, `.mkv` ou `.avi`, sozinha,
não garante reprodução. Em caso de incompatibilidade, a interface apresenta uma mensagem e o vídeo pode ser aberto
na versão clássica com VLC. Não existe conversão automática nem fallback silencioso para VLC na versão web.

O layout se adapta ao tamanho da janela e empilha os painéis em larguras pequenas. Isso não transforma a aplicação
em um serviço web público nem constitui suporte a Android/iOS.

### Validação

```powershell
uv run black --line-length 120 .
uv run ruff check .
uv run python -m pytest -q
```

O teste integrado opcional abre uma janela real e valida os formulários, reprodução, busca, legendas, persistência
compatível com a interface clássica e diferentes tamanhos de janela. Ele copia **somente os vídeos fornecidos** para
uma pasta temporária e cria seus próprios dados de teste; não altera os arquivos originais ou seus arquivos laterais:

```powershell
uv run --extra webview python -m tests.webview_smoke "C:\Videos\amostra.mp4" "C:\Videos\amostra.webm"
```

Use amostras curtas com duração superior a 9 segundos para a primeira amostra e superior a 1 segundo para as demais.
No Windows foram verificadas janelas de 1440×900, 1024×768, 860×620 e 640×700, além da inspeção visual da janela inicial.
Esses testes não substituem a avaliação com vídeos reais nem comprovam saída de áudio nos alto-falantes.

## Gerando Executável (.exe)

Para gerar uma versão executável standalone no Windows:

- **Via terminal**: Execute `uv run python build.py` ou `python build.py`.
- **Via clique duplo**: Clique duas vezes no arquivo [`build.bat`](file:///c:/Users/eduar/Desktop/chapter_editor/build.bat).

O executável final será gerado dentro do diretório `dist/EditorDeCapitulos.exe`.

### Versão webview

Para gerar um executável separado com a interface webview no Windows:

```powershell
uv run --extra webview --group dev python build.py --webview
```

Também é possível clicar duas vezes em **build_webview.bat**, que executa o mesmo comando a partir da pasta do projeto.
O resultado é **dist/EditorDeCapitulosWebview.exe**. O build clássico continua disponível por `build.bat` ou
`uv run python build.py`, e seu executável não é substituído pelo build webview.

O executável webview inclui Python, as dependências da interface e os arquivos HTML/CSS/JavaScript locais.
Ele não precisa de uma instalação de Python, de um servidor externo ou de VLC no computador de destino.
O **Microsoft Edge WebView2 Runtime** e o **.NET Framework 4.6.2 ou superior**, usados pelo pywebview no Windows,
devem estar instalados no destino. O build não instala nem incorpora esses runtimes do sistema.
O suporte a codecs segue as mesmas condições da execução em código-fonte.

Distribua o executável, sem incluir os vídeos ou arquivos de teste da pasta `build/`. Um `config.json` opcional
ao lado do executável permite reaproveitar as preferências; os arquivos `.chp` e `.srt` continuam junto dos vídeos.
Os recursos da interface são extraídos automaticamente para uma pasta temporária pelo PyInstaller ao abrir o `.exe`.
O build usa caminhos relativos à localização de `build.py`, independentemente da pasta atual do terminal.

O símbolo verde do cabeçalho também é o ícone da janela e do executável webview. O desenho original fica em
`web_ui/app-icon.svg`; suas versões PNG e ICO (16 a 256 pixels) podem ser regeneradas com
`uv run python scripts/generate_icon.py`. Os três arquivos são incluídos no build webview.

O executável webview foi gerado e aberto no Windows local a partir de outra pasta, com carregamento dos recursos
empacotados, leitura dos capítulos e reprodução de uma amostra MP4. Essa verificação não substitui um teste de
instalação em outro computador sem as ferramentas de desenvolvimento.

