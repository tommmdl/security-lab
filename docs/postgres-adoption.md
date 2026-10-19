# O Alpine agora é o banco dos labs

Português · [English](postgres-adoption.en.md)

Docker e Kubernetes passaram a usar PostgreSQL 17.11/Alpine 3.24.2, com libxml2 2.13.9-r2, zlib 1.3.2-r1 e o gosu reconstruído. A imagem é a mesma que passou pelos testes e foi publicada antes da adoção:

`ghcr.io/tommmdl/docker-lab@sha256:8b6813ec76804698c33e4dac8f501ca8f641affcbd27cbc3b7dd6fdb02874fc3`

A [análise anterior](postgres-alternative.md) mantém os relatórios completos de todas as tentativas. A adoção não transforma os achados antigos em falsos positivos: o Debian guardado para recuperação continua afetado, e a API também continua bloqueada. A matriz acompanha o banco ativo e mantém um alvo separado para o Bookworm de rollback. Zero achados é o resultado datado do Trivy, não uma garantia permanente.

## Como protegemos os dados

A mudança foi lógica: pg_dump custom, sem owner/ACL, e pg_restore em volume vazio, numa transação com interrupção no primeiro erro. Nenhum PGDATA Debian foi aberto pelo Alpine. Os dois usam PostgreSQL 17, mas mudam libc/glibc para musl, UID 999 para 70 e o locale de libc/en_US.utf8 para ICU/en-US/UTF8.

As escritas ficaram pausadas durante cada backup e troca: API parada no Compose; Deployment em zero no Kubernetes, aguardando os Pods terminarem. Neste lab a API é o único escritor externo. Mantivemos o acesso administrativo local e não restauramos credenciais globais. O hook recria as contas com os limites e as restrições de privilégio existentes.

Os backups privados ficam em `security-lab/.local/postgres-adoption/`: dumps de origem, dumps reversos, configuração de recuperação e comparação de linhas. Esse diretório é ignorado pelo Git; os relatórios públicos contêm hashes e resultados, sem conteúdo de notas ou senhas. Os volumes originais continuam guardados. Isto não cobre perda da máquina nem substitui uma cópia externa de backup.

O volume ativo do Docker é `docker-lab_pgdata_alpine_v1`. O original `docker-lab_pgdata` permanece intacto. No Kubernetes, o ativo é `data-postgres-alpine-0`; `data-postgres-0` mantém o UID original. O StatefulSet `postgres` fica com zero réplicas, e `postgres-alpine` recebe as conexões pelo Service estável `postgres`. O banco antigo não participa do selector ativo.

## O rollback foi exercitado pela aplicação

Em cada lab, criamos uma nota controlada depois da primeira troca para Alpine. Paramos novamente as escritas, exportamos o estado atual e restauramos em **outro volume Debian vazio**. Comparamos todos os campos das notas e o estado da sequência de IDs. Depois conectamos a API de verdade ao Debian e lemos a nota criada depois da migração.

Voltamos ao Alpine e removemos apenas a nota controlada. Os dados que existiam antes coincidiram no fim; a sequência pode avançar pelos testes e não é rebobinada. Recriamos o container/Pod do banco e conferimos novamente a persistência. Os bancos originais estavam vazios nesta execução; o teste anterior com sete notas Unicode e o teste atual com escrita após a troca complementam esse cenário, sem simular que havia dados de usuário.

Os volumes de rollback restaurados também ficam retidos. No Kubernetes o StatefulSet temporário de rollback termina com zero réplicas; ele não é gerenciado pelo Argo CD e seu nome real fica no arquivo privado `kubernetes-state.json`. Nenhum comando de limpeza com remoção de volumes foi usado nos ambientes existentes.

## Reproduzir a adoção em uma cópia ainda Debian

O [script da operação](../scripts/adopt-postgres.py) atende estes checkouts irmãos do portfólio, com as contas já endurecidas e o Argo CD `notes` já instalado. Não é uma ferramenta genérica de migração. Execute a partir da pasta que contém `docker-lab`, `kubernetes-lab` e `security-lab`:

```bash
python3 security-lab/scripts/adopt-postgres.py snapshot
python3 security-lab/scripts/adopt-postgres.py docker
python3 security-lab/scripts/adopt-postgres.py kubernetes
```

O snapshot não sobrescreve um snapshot existente. As etapas recusam uma origem já trocada ou um destino existente; não reexecute a migração sobre os labs já adotados. O script captura a configuração de origem e para as escritas; os arquivos privados de configuração permitem recuperar uma etapa interrompida. Uma falha interrompe a operação, sem remover os volumes ou reativar automaticamente as escritas.

O Kubernetes pausa a automação do Argo antes de alterar o estado vivo. Depois do teste, publique os manifests atualizados de `argocd-lab/workloads/notes/postgres.yaml`, confira o resultado renderizado de `workloads/notes-traced` e só então restaure `automated: {prune: false, selfHeal: true}`. A API instrumentada e seus destinos de observabilidade continuam os mesmos. Aplicar somente o repositório Kubernetes não altera a fonte Git que o Argo acompanha.

Novas instalações do Compose usam diretamente o digest aprovado e um volume Alpine. O wrapper recusa uma troca automática quando reconhece o volume Debian antigo. O bootstrap Kubernetes também recusa prosseguir enquanto detectar o StatefulSet antigo ativo. Em uma instalação existente, siga a migração em vez de executar `up` esperando que ela aconteça sozinha.

## Recuperação depois de novas escritas

Os dumps guardados têm um horário. Ligar a API ao volume original mais tarde descartaria as escritas feitas só no Alpine. Para um rollback futuro: pause as escritas, faça **novo dump do Alpine atual**, restaure em **novo volume Debian vazio**, compare linhas, esquema, permissões relevantes e sequência e então altere o destino da aplicação. Teste readiness e leitura antes de liberar escritas. O locale de retorno precisa ser revisto se surgirem índices/consultas de texto dependentes dele ou novas extensões.

No Docker, os arquivos privados `docker-target-compose.json` e `docker-rollback-compose.json` registram o que foi usado. O comando que operou cada configuração foi:

```bash
bash docker-lab/scripts/compose.sh -p docker-lab -f CAMINHO_DO_ARQUIVO_PRIVADO up -d --no-build --wait
```

Não use o arquivo de rollback antigo para aceitar escritas atuais: ele é uma fotografia do ensaio. Se um rollback definitivo for necessário, atualize também o Compose padrão para a imagem e o volume restaurado antes de retomar o uso habitual; um `up` padrão não deve reconectar a aplicação a dados Alpine antigos.

No Kubernetes, pause o Argo, reduza a API a zero, restaure em PVC novo com a imagem/UID Debian e altere o selector do Service `postgres` para esse banco. Atualize a fonte Git com o destino escolhido antes de reativar self-heal. `rollout undo` de imagem não converte diretórios de dados nem substitui restauração lógica.

Resultados públicos: [Docker](../evidence/postgres-adoption/docker.json), [Kubernetes](../evidence/postgres-adoption/kubernetes.json). As evidências adicionais de API, privilégios, GitOps e scanner acompanham esse diretório. Os relatórios anteriores continuam nos diretórios históricos.

## Conferência das integrações

A imagem ativa continua com zero achados na análise remota completa registrada. Passaram 23 testes da API e 20 de privilégios/recursos no Docker; no Kubernetes, 20 de privilégios/segurança. O self-heal do Argo corrigiu dois desvios de réplicas, preservando o PVC ativo e a nota do teste. Logging passou em 16 verificações e tracing em 19. A descoberta do Alloy e a consulta do painel PostgreSQL agora incluem `notes-db-alpine`, mantendo o histórico `notes-db`; o teste de logging escolhe o banco ativo pelo Service. A demonstração GHCR separada continua na imagem anterior e fica fora desta troca dos dois labs.

O [CI do Kubernetes](https://github.com/tommmdl/kubernetes-lab/actions/runs/39182856357) passou nos 24 testes de recuperação, persistência e rollback em cluster novo. O [CI de segurança](https://github.com/tommmdl/security-lab/actions/runs/39183015128) aprovou os 15 testes da política e o banco ativo `postgres`; API e `postgres-bookworm` permaneceram bloqueados. Os relatórios completos acompanham as evidências, sem supressões.

Depois da mudança do padrão, repetimos a regressão com sete notas Unicode: passaram 17 verificações de migração, 23 da API e 20 de segurança. A regressão histórica de endurecimento das contas também passou, somente em imagens Debian descartáveis. Ela sobrescreve explicitamente o novo padrão e a inicialização, evitando que esse teste antigo tente trocar fisicamente um diretório Debian por Alpine.

O [CI de logging](https://github.com/tommmdl/logging-lab/actions/runs/39183020303) também passou nas 16 verificações. A execução viva com Alpine está coberta pela evidência local de logging; o lab de publicação e os demais commits de origem históricos não foram avançados silenciosamente.
