# Arquitetura e armazenamento

## Organização do projeto

| Arquivo ou diretório | Responsabilidade |
| --- | --- |
| `app.py`, `gui/` | Entrada e componentes da interface clássica Tkinter/VLC. |
| `web_app.py` | Entrada pywebview, seletores nativos e ponte entre JavaScript e Python. |
| `web_ui/` | HTML, CSS, JavaScript e ícones locais da interface webview. |
| `web_backend.py` | Sessão de edição, detecção de alterações externas e servidor de mídia em loopback. |
| `logic.py` | Validação e persistência compartilhada dos projetos `.chp` e das legendas `.srt`. |
| `config.py` | Valores padrão, normalização e leitura/gravação das preferências. |
| `app_storage.py` | Abertura transacional de `config.vdb`, versão de esquema e migração das fontes antigas. |
| `video_history.py` | Inclusão, consulta e descoberta de vídeos com recursos salvos. |
| `build.py`, `build*.bat` | Empacotamento PyInstaller de cada interface no Windows. |
| `scripts/generate_icon.py` | Geração dos PNG/ICO a partir do SVG da aplicação. |
| `tests/` | Testes de domínio, interfaces, persistência e cenário integrado WebView2. |

A interface web chama a ponte Python para abrir arquivos, salvar recursos, gravar preferências e consultar a
biblioteca. O JavaScript não grava bancos diretamente. A interface clássica reutiliza o domínio e as preferências,
mas seus componentes não dependem da interface web. Os esquemas SQL são definidos no código-fonte; não é necessário
versionar uma cópia de banco pessoal para reconstruir a estrutura.

## Banco da aplicação: `config.vdb`

Apesar da extensão própria, o arquivo é um banco SQLite. Fica junto do código-fonte ou do executável, conforme
`config._application_dir()`. O diretório precisa permitir escrita; não há seleção automática de uma pasta de perfil
do usuário quando a aplicação está instalada em um diretório protegido.

O esquema atual é identificado por `app_metadata.schema_version = "1"`, representado como linha de chave/valor:

| Tabela | Colunas | Finalidade |
| --- | --- | --- |
| `app_metadata` | `key TEXT PRIMARY KEY`, `value TEXT NOT NULL` | Metadados do banco; a chave `schema_version` contém `1`. |
| `settings` | `key TEXT PRIMARY KEY`, `value TEXT NOT NULL` | Uma preferência por linha; o valor é serializado como JSON. |
| `videos` | `key TEXT PRIMARY KEY`, `path TEXT NOT NULL`, `accessed TEXT NOT NULL` | Caminho normalizado, caminho de exibição e instante UTC em ISO 8601. |

Os limites e os padrões são definidos em `config.DEFAULT_CONFIG` e `normalize_config()`:

| Preferência | Padrão | Validação e uso |
| --- | --- | --- |
| `update_ms` | `500` | Inteiro de 50 a 60000 ms; atualização da interface clássica. |
| `small_jump` | `5` | Inteiro de 1 a 3600 s; botões e atalhos curtos. |
| `large_jump` | `20` | Inteiro de 1 a 3600 s; barra de progresso e atalhos longos. |
| `video_scroll_jump` | `5` | Inteiro de 1 a 3600 s; scroll sobre a prévia na interface web. |
| `track_scroll_jump` | `20` | Inteiro de 1 a 3600 s; scroll na régua e faixa de capítulos na interface web. |
| `volume` | `100` | Inteiro de 0 a 100; valor inicial. A interface clássica persiste ajustes; a web altera somente a sessão. |
| `always_on_top` | `false` | Booleano; a janela web lê na inicialização, a clássica permite alternar. |
| `window_geometry` | `""` | Texto; geometria da janela clássica. |
| `last_video` | `""` | Texto; estado usado pela interface clássica, separado da biblioteca. |
| `keys` | Espaço, setas e Shift + setas | Objeto JSON com `play_pause`, `back_small`, `fwd_small`, `back_large`, `fwd_large`. |

Carregar as preferências completa campos ausentes ou inválidos com os padrões. Gravar preferências atualiza somente
a tabela `settings`; gravar a biblioteca atualiza somente `videos`. As duas operações usam transações e não
substituem o arquivo completo. Uma versão de esquema diferente de `1` é recusada; não há migração entre versões
futuras implementada neste momento.

### Migração dos arquivos anteriores

Quando não existe o marcador de versão no banco de destino:

1. A aplicação lê o `config.json` da mesma pasta, se existir, exigindo um objeto JSON.
2. Lê `video_history.sqlite3`, se existir, em modo somente leitura, usando a tabela antiga `videos`.
3. Insere preferências, histórico e marcador de versão em uma única transação.

Uma falha desfaz a transação inteira. Uma tentativa posterior pode repetir a migração depois de a fonte ser
recuperada. As fontes antigas não são apagadas, renomeadas nem alteradas. Depois de concluída, a migração não é
repetida, mesmo que os arquivos antigos mudem. Uma execução nova sem fontes antigas também marca a inicialização
como concluída; copiar arquivos antigos para essa pasta posteriormente não os importa automaticamente.

Falhas de leitura de configuração são expostas como `ConfigLoadError`, com tentativa de cópia de recuperação.
Uma falha ao registrar um recurso já salvo na biblioteca gera um aviso, sem declarar que o salvamento do projeto
falhou. Um banco ilegível não é substituído por padrões. Um destino inicialmente inexistente pode ficar como um
arquivo SQLite vazio após uma migração malsucedida; isso não significa migração concluída.
Uma preferência armazenada com JSON inválido também bloqueia a gravação, para que o fechamento de uma sessão
iniciada com padrões não sobrescreva as demais preferências recuperáveis. É necessário recuperar a fonte afetada.

## Projetos por vídeo: `.chp` e `.srt`

Os caminhos laterais usam o nome do vídeo sem a extensão. Assim, `aula.mp4` e `aula.mkv` na mesma pasta compartilham
`aula.chp` e `aula.srt`. Diferencie o nome-base dos vídeos quando precisar de projetos independentes.

O `.chp` é SQLite e contém o esquema definido por `ChapterManager._create_schema()`:

| Tabela | Conteúdo e relacionamentos |
| --- | --- |
| `chapters` | `id`, `parent_id`, `position`, `title`, `start`, `end`; árvore por chave estrangeira com exclusão em cascata. |
| `casting` | `id`, `position`, `name`; integrantes do elenco. |
| `metadata` | `id`, `parent_id`, `position`, `key`, `value`; árvore de chaves com exclusão em cascata. |
| `images` | `id`, `title`, `description`, `width`, `height`, `mime_type`, `data`; imagens recortadas armazenadas como BLOB. |
| `image_links` | `image_id`, `record_type`, `record_id`, `position`; associações a capítulos, elenco e metadados. |

Os tipos de vínculo são restringidos por SQL. O identificador do registro associado é validado pela aplicação;
não há uma chave estrangeira polimórfica para as três tabelas. Tempos de capítulos são segundos inteiros.
As gravações validam os registros e substituem o conteúdo do projeto em uma transação.

**O formato `.chp` ainda não possui marcador de versão de esquema.** A criação é idempotente com `CREATE TABLE IF
NOT EXISTS`; isso não equivale a uma migração de colunas ou a uma proteção contra formatos de versões futuras.
Antes de alterar sua estrutura, é necessário definir uma versão inicial e uma política de migração/compatibilidade.

As legendas usam SRT, com precisão de milissegundos e salvamento atômico; a versão anterior é mantida em `.srt.bak`.
Salvar somente legendas não cria `.chp`. A simples abertura sem arquivos laterais não cria um projeto vazio.

## Regras da biblioteca

O cadastro automático ocorre na interface web, após salvar um recurso com sucesso ou ao abrir um vídeo que já tenha
`.chp` ou `.srt`. A interface clássica não registra automaticamente a biblioteca: seus projetos podem ser descobertos
ao abrir o vídeo na web ou ao usar **Adicionar pasta**. A busca por pasta inclui subpastas e não segue diretórios
simbólicos por padrão. Os formatos candidatos estão em `VIDEO_SUFFIXES`.

O caminho absoluto normalizado identifica o vídeo. No Windows, a normalização ignora diferenças de maiúsculas e
minúsculas; não existe identificação pelo conteúdo. A importação usa inicialmente a data de modificação mais recente
dos recursos como referência de ordenação; abrir ou salvar o vídeo atualiza seu acesso. A listagem converte a data
UTC para a apresentação local. Vídeos indisponíveis continuam no índice, com a abertura desabilitada.

Não há reprodução sequencial automática, limite de entradas, remoção manual, função de relocalização de arquivos
nem fusão de entradas após mudanças de caminho.

## Backup, versionamento e validação

Para preservar o trabalho, guarde os vídeos, seus `.chp` e `.srt` e o `config.vdb`. Copie os bancos com a aplicação
fechada. A biblioteca contém caminhos, não cópias dos vídeos. O `.gitignore` não é uma estratégia de backup.

Código, SQL de criação/migração, documentação, testes, dependências e ícones pertencem ao Git. Dados pessoais,
caches, backups e resultados de build ficam ignorados. Arquivos novos só passam a ser rastreados após inclusão
explícita no Git; a existência no diretório não significa que já foram versionados ou commitados.

Os comandos de validação e os pré-requisitos estão no README. Os testes cobrem persistência, rollback, migração
única, erros de dados, abertura da biblioteca e regras de domínio. O cenário WebView2 usa dados temporários e
verifica a interface real. A validação do código-fonte não valida automaticamente um executável previamente gerado.
Não há automação de integração contínua versionada no repositório neste momento.

## Decisões ainda abertas

- Definir versionamento e migrações do esquema `.chp` antes de uma mudança em suas tabelas.
- Decidir se a interface clássica precisa de biblioteca e saltos por área equivalentes aos da interface web.
- Decidir se volume na interface web deve persistir entre sessões.
- Definir relocalização/remoção de entradas da biblioteca e eventual reprodução sequencial, se desejadas.
- Definir uma pasta de dados por usuário caso seja necessário instalar em diretórios sem permissão de escrita.
- Definir integração contínua e um processo de distribuição que valide o executável de cada versão.
