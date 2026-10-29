# Video Player/Editor

Editor desktop em Python 3.12 para capítulos, legendas, elenco, metadados e imagens associados a vídeos locais.
Possui uma interface clássica em Tkinter/VLC e uma interface alternativa em pywebview com reprodução HTML5.

A organização dos módulos, os esquemas de armazenamento e as limitações conhecidas estão descritos em
[Arquitetura e armazenamento](docs/ARQUITETURA.md).

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
- Importação de arquivos de imagem limitada a JPG/JPEG, GIF, PNG e WebP nas duas interfaces; os demais
  formatos, incluindo AVIF, são recusados pelo conteúdo, mesmo com extensão alterada. Imagens animadas são
  usadas como um quadro estático no recorte. Não há conversão prévia de formatos não suportados.
- Arquivo `.chp` (SQLite) por vídeo para capítulos, elenco, metadados e imagens; imagens são armazenadas como dados binários recortados, sem manter o original
- Menu para abrir novos arquivos
- Banco SQLite `config.vdb`, mantido ao lado do `app.py` ou do executável, armazena:
  - Intervalo de atualização da interface
  - Tempo dos saltos rápidos (curto e longo)
  - Teclas de atalho para play/pause e avanço/retrocesso
  - Nível de volume do player
  - Biblioteca de vídeos com recursos salvos
- Botões de avançar/retroceder
- Roda do mouse sobre a barra de progresso para saltos longos
- Controles reorganizados em duas linhas com tempo e barra de progresso na parte superior e botões de reprodução na inferior
- Ações de adicionar e remover posicionadas no topo dos painéis, com seleção automática do item recém-criado
- Tela de configurações para definir atalhos (basta pressionar a tecla desejada)
- Validação dos intervalos de capítulos, subcapítulos e legendas antes do salvamento
- Salvamento atômico das legendas, com cópia `.bak` da versão anterior; os dados `.chp` são gravados em transações SQLite
- Tentativa de preservar configurações ilegíveis em `.corrompido_*.bak`; os padrões valem apenas para a sessão
  e não substituem um banco ilegível

## Instalação

1. Certifique-se de ter o Python 3.12 instalado.
2. Instale as dependências com `uv sync --dev`.

## Uso

Execute `python app.py` (ou `uv run python app.py`) para iniciar o programa e escolha o vídeo que deseja editar.

Ao salvar capítulos, elenco, metadados ou imagens, o aplicativo cria um `.chp` SQLite ao lado do vídeo.
Legendas são gravadas separadamente em `.srt` e, sozinhas, não criam `.chp`. Apenas abrir um vídeo sem recursos
existentes não cria esses arquivos. Arquivos JSON antigos de **projeto** não são convertidos automaticamente;
a migração de `config.json`, descrita abaixo, refere-se somente às preferências da aplicação.

O `config.vdb` é resolvido pelo local da aplicação, independentemente do diretório em que o comando foi executado. No
modo fonte ele fica ao lado de `app.py`; no executável ele fica ao lado de `EditorDeCapitulos.exe`.

Configurações e biblioteca compartilham esse único arquivo SQLite, com tabelas separadas. Na primeira execução,
o aplicativo importa automaticamente as preferências de `config.json` e o histórico de `video_history.sqlite3`
existentes na mesma pasta. A importação ocorre em uma transação e não apaga nem altera os arquivos antigos.
Depois da migração, somente `config.vdb` é usado; mudanças posteriores nos arquivos antigos não são reimportadas.
Se uma fonte antiga estiver ilegível, a migração é interrompida sem substituir os dados por valores padrão.
Os arquivos `.chp` e `.srt` de cada vídeo permanecem junto dos vídeos e não são incorporados ao banco da aplicação.
Evite editar diretamente o banco enquanto o aplicativo estiver aberto; use a tela de configurações.

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

- **Biblioteca**, ao lado de **Abrir vídeo**, mantém entre sessões a lista de vídeos com qualquer recurso salvo,
  incluindo legendas `.srt`. Abrir um vídeo sem salvar recursos não o inclui nem cria seu `.chp`.
  Vídeos com `.chp` ou `.srt` existentes entram na biblioteca ao serem abertos. Para localizar projetos antigos,
  use **Adicionar pasta**: a busca inclui as subpastas e reconhece os formatos de vídeo do seletor.
  A biblioteca permite buscar por nome ou caminho e reabrir o vídeo com seus recursos, ordenando os mais recentes
  primeiro. Arquivos movidos ou apagados permanecem sinalizados como indisponíveis.
  O índice fica no mesmo `config.vdb` das configurações, ao lado da aplicação ou executável e separado dos
  projetos. Não há limite de quantidade nem reprodução automática em sequência.
- Reprodução HTML5 com pausa, saltos, volume, silenciamento, tela cheia e linha do tempo proporcional. Subcapítulos
  são desenhados por cima dos pais, na mesma faixa. Capítulos principais simultâneos usam faixas diferentes;
  capítulos sem sobreposição temporal podem compartilhar a faixa. Há rolagem vertical para projetos maiores.
- Atalhos e intervalos de salto lidos do `config.vdb`; os atalhos não interferem na digitação dos formulários.
- Engrenagem no cabeçalho da prévia para abrir **Configurações**: ajuste o salto do scroll sobre a barra de
  progresso e o salto dos botões ao lado do play, em segundos inteiros de 1 a 3600. **Salvar configurações**
  aplica os valores imediatamente e os mantém no `config.vdb` entre sessões; **Cancelar** descarta a edição.
  O scroll compartilha o intervalo do salto longo do teclado e os botões compartilham o salto curto.
  A lista de **Atalhos de teclado** fica dentro dessa tela; a tecla **?** também abre as configurações.
- O scroll sobre o **vídeo** e sobre a **linha do tempo** (régua e faixa de capítulos) possui intervalos
  independentes, também ajustáveis nas configurações. Os padrões são 5 segundos sobre o vídeo e 20 segundos
  sobre a linha do tempo. Rolar para cima avança; para baixo retrocede, respeitando o início e o fim do vídeo.
  Os intervalos dos botões, da barra de progresso e dos atalhos continuam separados desses dois ajustes.
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
permite editar os intervalos de salto na interface web; as teclas de reprodução continuam editáveis na interface clássica.

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
uv run python -m py_compile (rg --files -g '*.py')
uv run python -m pytest -q
```

O teste integrado opcional abre uma janela real e valida os formulários, reprodução, busca, legendas, persistência
compatível com a interface clássica e diferentes tamanhos de janela. Ele copia **somente os vídeos fornecidos** para
uma pasta temporária e cria seus próprios dados de teste; não altera os arquivos originais ou seus arquivos laterais:

```powershell
uv run --extra webview python -m tests.webview_smoke "C:\Videos\amostra.mp4" "C:\Videos\amostra.webm"
```

O comando de sintaxe acima usa PowerShell e exige `rg` (ripgrep). Os testes Tkinter exigem uma sessão gráfica;
os testes do servidor usam loopback e os de persistência precisam criar e alterar arquivos temporários.

Use amostras curtas com duração superior a 9 segundos para a primeira amostra e superior a 1 segundo para as demais.
No Windows foram verificadas janelas de 1440×900, 1024×768, 860×620 e 640×700, além da inspeção visual da janela inicial.
Esses testes não substituem a avaliação com vídeos reais nem comprovam saída de áudio nos alto-falantes.

## Gerando Executável (.exe)

Para gerar uma versão executável standalone no Windows:

- **Via terminal**: Execute `uv run python build.py` ou `python build.py`.
- **Via clique duplo**: Clique duas vezes no arquivo [build.bat](build.bat).

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

Distribua o executável, sem incluir os vídeos ou arquivos de teste da pasta `build/`. Para levar as preferências
e a biblioteca para outra instalação, copie o `config.vdb` com o aplicativo fechado e coloque-o ao lado do executável.
Os arquivos `.chp` e `.srt` continuam junto dos vídeos. Caminhos da biblioteca precisam continuar acessíveis no destino.
Os recursos da interface são extraídos automaticamente para uma pasta temporária pelo PyInstaller ao abrir o `.exe`.
O build usa caminhos relativos à localização de `build.py`, independentemente da pasta atual do terminal.
Os dois builds excluem explicitamente o plugin AVIF e sua extensão nativa do Pillow.

O símbolo verde do cabeçalho também é o ícone da janela e do executável webview. O desenho original fica em
`web_ui/app-icon.svg`; suas versões PNG e ICO (16 a 256 pixels) podem ser regeneradas com
`uv run python scripts/generate_icon.py`. Os três arquivos são incluídos no build webview.

O executável webview foi gerado e aberto no Windows local a partir de outra pasta, com carregamento dos recursos
empacotados, leitura dos capítulos e reprodução de uma amostra MP4. Essa verificação não substitui um teste de
instalação em outro computador sem as ferramentas de desenvolvimento.

## Versionamento e dados locais

O repositório deve conter código-fonte, testes, documentação, `pyproject.toml`, `uv.lock`, scripts de build e
os ícones da aplicação. As definições das tabelas ficam no código-fonte: `app_storage.py` para `config.vdb`
e `logic.py` para `.chp`. O banco local e os projetos pessoais não substituem essas definições no Git.

O `.gitignore` exclui ambientes virtuais, caches, relatórios de cobertura, builds, executáveis gerados,
configurações locais, bancos de histórico antigos, arquivos `.chp`, legendas e vídeos pessoais.
A pasta `tests/fixtures/` é uma exceção para amostras sintéticas que se decida versionar explicitamente.
Ignorar um arquivo não remove um arquivo já rastreado: confira `git status --short` e `git ls-files` antes de cada commit.
Os commits dependem de autorização expressa e devem seguir as instruções de `AGENTS.md`.

