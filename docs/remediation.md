# Corrigindo o que dá, sem tirar o restante da vista

Português · [English](remediation.en.md)

Começamos pelos achados que tinham correção publicada na base do Trivy. Mantivemos a versão do scanner, a plataforma e a política de bloqueio. Nenhuma CVE entrou em lista de exceções, e os achados sem correção continuam contando.

| Imagem | Total antes → depois | HIGH antes → depois | CRITICAL antes → depois | Achados com correção depois |
|---|---:|---:|---:|---:|
| API | 173 → 164 | 48 → 44 | 0 → 0 | 0 |
| PostgreSQL | 472 → 412 | 95 → 71 | 4 → 3 | 0 |

São ocorrências reportadas, não uma contagem de CVEs únicas. A [comparação](../evidence/remediation/comparison.json) registra a data da base e os hashes dos relatórios. Os JSONs completos de antes e depois estão ao lado dela, incluindo LOW, MEDIUM, UNKNOWN e achados sem correção. As evidências do exercício anterior foram preservadas.

## O que mudou

A API instala as dependências no build e depois remove pip e ensurepip da imagem final. As cópias vulneráveis de msgpack, setuptools e urllib3 pertenciam às ferramentas internas do pip; instalar versões novas como pacotes separados não substituiria essas cópias. Removemos o instalador desnecessário, incluindo suas wheels embutidas, em vez de esconder metadados de pacotes. O Flask passa para 3.1.3 e o liblzma5 do Debian para 5.8.1-1+deb13u2.

A imagem do PostgreSQL mantém a versão 17.11, o Bookworm, o entrypoint original e a organização dos dados. O auxiliar gosu 1.19 é recompilado a partir do commit oficial `6456aaa0f3c854d199d0f037f068eb97515b7513`, usando Go 1.27.2, moby/sys/user 0.4.1 e x/sys 0.44.0. As atualizações dos módulos modificam intencionalmente essa cópia da fonte; os metadados do Go registram `vcs.modified=true`. O compilador fica na etapa de build. A troca de usuário é conferida no build e a inicialização do banco é exercitada pelos testes do Compose.

As fontes da API e do banco ficam no [docker-lab](https://github.com/tommmdl/docker-lab). O [github-actions-lab](https://github.com/tommmdl/github-actions-lab) constrói as duas imagens, testa o conjunto e publica os mesmos IDs testados. As duas usam o pacote público existente no GHCR; as tags do banco têm o prefixo `postgres-`. A publicação não depende do gate de segurança separado, então publicar uma imagem com correções não é uma aprovação de segurança.

## O que continua pendente

O gate continua bloqueando as duas imagens: 44 ocorrências HIGH na API e 71 HIGH mais 3 CRITICAL no PostgreSQL. Nenhum achado restante tem FixedVersion nessa fotografia da base. Isso não prova que não exista mitigação ou que um aviso não possa mudar.

As CVEs críticas restantes no PostgreSQL são CVE-2025-7458 (libsqlite3-0), CVE-2026-6653 (libxml2) e CVE-2023-45853 (zlib1g). Elas continuam nos relatórios e na saída do gate. A situação no fornecedor e a possibilidade real de exploração precisam de análise individual antes de qualquer exceção. Esta mudança não cria exceções nem afirma que as imagens estão prontas para produção.

## Verificações

Rodamos os 23 testes da API e do Compose em um projeto e volume separados, incluindo inicialização de um banco novo, persistência após recriar containers, respostas durante a parada do banco e recuperação. Antes de mexer no cluster em execução, salvamos um pg_dump privado e o restauramos em outro banco na imagem recompilada do PostgreSQL. A contagem de linhas e um checksum do conteúdo precisam coincidir. Backups e conteúdo das notas ficam fora do Git.

Para repetir a coleta sem filtros: `python3 scripts/scan.py notes-api` e `python3 scripts/scan.py postgres`. A saída 1 indica que o gate mantido bloqueou os achados restantes. Os relatórios completos JSON e SARIF são guardados pelo Actions mesmo quando ele falha. As contagens podem mudar quando a base de vulnerabilidades mudar.

Fontes: [Dockerfile oficial do PostgreSQL](https://github.com/docker-library/postgres/blob/master/17/bookworm/Dockerfile), [fonte do gosu](https://github.com/tianon/gosu/tree/6456aaa0f3c854d199d0f037f068eb97515b7513), [versões do Go](https://go.dev/dl/).
