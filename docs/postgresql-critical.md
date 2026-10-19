# Três críticos, três decisões diferentes

Português · [English](postgresql-critical.en.md)

Consultamos os avisos do Debian, inspecionamos a imagem real e testamos as mudanças em bancos descartáveis. Não acrescentamos exceções ou supressões VEX, não alteramos os relatórios e mantivemos a política de bloqueio.

| Achado | O que encontramos | Decisão |
|---|---|---|
| CVE-2025-7458 / SQLite | Biblioteca afetada, trazida pelo GPG e sem ligação com o servidor PostgreSQL. | Remover os pacotes sem uso na execução. |
| CVE-2026-6653 / libxml2 | Biblioteca afetada e carregada pelo PostgreSQL. | Reduzir privilégios e limitar recursos; continua vulnerável. |
| CVE-2023-45853 / zlib | O código MiniZip afetado não é compilado no binário Debian inspecionado. | Registrar a aplicabilidade, mantendo o achado no scan e no gate. |

## SQLite: remover uma dependência desnecessária

O [Debian](https://security-tracker.debian.org/tracker/CVE-2025-7458) mantém a versão Bookworm instalada como afetada, sem correção nessa versão estável. O aviso trata de consultas preparadas contra SQLite, não de SQL do PostgreSQL. Não reduzimos a severidade por causa dessa diferença.

A dependência reversa instalada é o GPG. O `ldd` não encontra SQLite no servidor PostgreSQL, e a simulação do apt preserva servidor e cliente. A imagem usa `apt-get purge --auto-remove libsqlite3-0`: saem a biblioteca, seus metadados e ferramentas de gerenciamento de chaves sem uso neste lab. O gpgv e os chaveiros do Debian continuam presentes para verificar assinaturas. Ferramentas ou extensões futuras que precisem de SQLite exigem nova análise.

O inventário passa de **144 para 128 pacotes**; as ocorrências, de **412 para 350**. HIGH passa de 71 para 68 e CRITICAL de 3 para 2. São ocorrências de pacote/aviso, não CVEs únicas. O [relatório completo](../evidence/critical-review/postgres-after.json) mantém todas as severidades. A [comparação](../evidence/critical-review/comparison.json) registra a base usada e o hash do relatório; o scan anterior foi preservado em `evidence/remediation/`.

## libxml2: controles compensatórios, sem declarar correção

O [Debian](https://security-tracker.debian.org/tracker/CVE-2026-6653) informa que a versão do Bookworm está afetada e tem correção adiada. A avaliação menor do Debian e a classificação CRITICAL do NVD ficam registradas; não trocamos uma pela outra.

O PostgreSQL carrega libxml2, inclusive para suas [funções XML](https://www.postgresql.org/docs/17/xml-limits-conformance.html). A API usa consultas parametrizadas e guarda o título em VARCHAR. Um título parecido com XML continua sendo texto nos testes. Isso limita o caminho HTTP normal, mas não prova ausência de exposição após obter acesso SQL: uma consulta XMLPARSE inofensiva **continua funcionando com a conta comum**. Não executamos um exploit XML malicioso.

Antes, a aplicação usava o superusuário criado na inicialização. O PostgreSQL exige que o [bootstrap OID 10 continue superusuário](https://github.com/postgres/postgres/blob/REL_17_STABLE/src/backend/commands/user.c). O script preserva esse usuário como `notes_bootstrap`, limpa sua senha e cria um novo `lab` comum, com o mesmo login/senha da API. Transfere apenas o banco e a tabela de notas, sem transferir catálogos do sistema; a sequência de identidade acompanha a tabela. Sessões antigas do bootstrap são encerradas na primeira migração.

O `lab` não pode assumir administradores, criar usuários, ler arquivos do servidor ou executar COPY PROGRAM. Ele continua dono do banco/tabela para as migrações do lab funcionarem: não é uma conta estritamente limitada a DML. O `notes_admin` permite manutenção por socket Unix. As duas contas administrativas ficam sem senha e com regras de rejeição por TCP antes das regras originais, incluindo loopback e replicação, conforme a [ordem do HBA](https://www.postgresql.org/docs/17/auth-pg-hba-conf.html). O acesso ao socket confiável dentro do container continua sendo uma fronteira administrativa.

O Compose limita o banco a 384 MiB, uma CPU e 256 PIDs, acrescenta no-new-privileges e mantém a porta sem publicação no host. No Kubernetes, o limite existente de 384 MiB ganha uma CPU; UID 999, capabilities removidas e seccomp são preservados. O ClusterIP ainda pode ser alcançado por outros Pods: não afirmamos que há NetworkPolicy aplicada pela rede padrão do kind.

A conta recebe padrões de 5 segundos por comando e 10 segundos para transação ociosa. Um usuário SQL pode alterar esses padrões, e falhas em código nativo podem não responder prontamente à interrupção. Cgroups limitam recursos do host, mas não garantem disponibilidade do banco nem impedem uma falha de memória. **A libxml2 não foi corrigida; sua CVE continua bloqueando o gate.**

## zlib: o aviso da fonte e o binário distribuído

O [Debian](https://security-tracker.debian.org/tracker/CVE-2023-45853) explica que o pacote binário do Bookworm não compila o contrib/minizip afetado. Inspecionamos a libz real: guardamos seu checksum e símbolos dinâmicos, sem encontrar `zipOpenNewFileInZip4_64`. O inventário de pacotes e nomes de arquivos não encontrou MiniZip ou pyminizip. Veja as [evidências de aplicabilidade](../evidence/critical-review/zlib-applicability.json).

Esses resultados sustentam que o código afetado está ausente da biblioteca empacotada inspecionada. Não provam que todo possível binário de terceiros com bibliotecas estáticas esteja livre do problema. A zlib continua necessária e instalada. O Trivy ainda reporta a CVE como CRITICAL e o gate continua contando o achado. Não há exceção, VEX ou alteração do JSON para produzir um resultado verde.

## Atualização e testes

Bancos novos executam o hook da imagem. Volumes existentes precisam de migração explícita depois da troca de imagem; os hooks não se repetem. Backups de dados, objetos globais e HBA ficam fora do Git. O [guia de operação](https://github.com/tommmdl/docker-lab/blob/main/docs/database-hardening.md) explica os comandos e os limites da migração, feita apenas para `notes`/`lab`. Voltar a imagem não desfaz as contas ou o HBA persistidos.

Os **20 testes de segurança** verificam negações reais de privilégios, rejeição TCP dos administradores, timeouts, limites e exposição XML restante. Os **23 testes de integração** cobrem API e persistência. O teste de atualização cria três notas na imagem anterior, troca a imagem no mesmo volume, migra as contas, encerra uma sessão privilegiada mantida aberta e compara todos os campos das notas. O login é preservado e a execução repetida do endurecimento também é testada. Ele remove apenas o ambiente temporário que criou.

Os JSONs e as inspeções ficam em [critical-review](../evidence/critical-review/). O gate continua bloqueando **68 HIGH e 2 CRITICAL**. A remoção do SQLite, a mitigação da libxml2 e a avaliação de aplicabilidade da zlib são resultados diferentes; nenhum deles é apresentado como um scan sem problemas.
