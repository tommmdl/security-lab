# A API Alpine passa a ser o padrão dos labs

Português · [English](api-adoption.en.md)

O Docker e os manifests básicos do Kubernetes agora apontam para a API Alpine publicada. O workload principal com OpenTelemetry, gerenciado pelo Argo CD, aponta para a derivada Alpine instrumentada. São os mesmos digests que passaram pelo [ensaio separado](api-alpine.md):

- Básica: `ghcr.io/tommmdl/docker-lab@sha256:ae2e93fdbab7bc912897e6524b3e17b982e97cfb29bcb4fc36d9c014d615eb91`.
- OpenTelemetry: `ghcr.io/tommmdl/docker-lab@sha256:e01c467c0987cc2d999778a4e9ee429bee1d6af4bcdef80e38ce620b95a0b8da`.

O runtime mantém Python 3.13.16, Flask 3.1.3 e Psycopg 3.3.6; a base passa a Alpine 3.24.2/musl. A derivada mantém as versões OpenTelemetry já testadas. Não houve conversão de banco, troca de credenciais ou mudança de schema nesta adoção. Os bancos PostgreSQL Alpine, seus containers/PVCs e os dados existentes continuam os mesmos.

## A proteção dos dados e o rollback real

Antes da troca, guardamos privadamente a configuração Compose resolvida, o Deployment e a configuração da Application do Argo. Fizemos pg_dump custom dos dois bancos. Cada backup foi restaurado em outro banco temporário, comparando todos os campos das notas, colunas, índices e estado da sequência. Só esses bancos de conferência, com nomes únicos gerados pela operação, foram removidos. Os dumps e a configuração de recuperação ficam em `security-lab/.local/api-adoption/`, fora do Git.

As APIs ficaram brevemente paradas durante a captura para comparar um estado consistente. A API é o único escritor externo previsto neste lab. As trocas seguintes no Kubernetes usaram rollout com duas réplicas; isso não é uma certificação geral de ausência de indisponibilidade. No Docker, recriar o container da API causa uma interrupção curta.

O teste não foi apenas `rollout undo` sem dados. No Docker, a API Alpine criou uma nota controlada com Unicode. Voltamos ao digest Debian anterior e lemos **todos os campos dessa mesma nota**, depois retornamos ao Alpine e conferimos novamente. O banco sequer teve seu container recriado.

No Kubernetes, testamos dois caminhos no Service principal: Alpine básica → Debian básica → Alpine básica; depois Alpine com OpenTelemetry → imagem instrumentada original → Alpine com OpenTelemetry. Uma nota escrita depois de cada primeira troca permaneceu acessível no rollback. A versão instrumentada anterior também foi exercitada com os testes reais de tracing antes da volta à nova versão.

Somente as notas criadas pela operação foram apagadas. Os dados que existiam antes foram comparados no final; a sequência pode avançar pelos testes e não foi rebobinada. Os backups continuam guardados. Não restauramos um dump antigo sobre o banco ativo, o que descartaria escritas novas.

## O que fica guardado para retornar

A básica Debian anterior continua publicada por digest:

`ghcr.io/tommmdl/docker-lab@sha256:343f2b23294c09bea9c3250a3b3fd1f95d817acea9db0231dfaaaf406f22fbac`

A instrumentada original era local: `tracing-lab-api:otel-c5d4e188167922bd`. Mantivemos a imagem e um arquivo Docker privado com hash, para não depender somente do cache dos nós. Seus fontes anteriores ficam em `instrumentation/Dockerfile.debian`, e o Dockerfile básico anterior em `docker-lab/images/api-debian/Dockerfile`. A imagem exata é o caminho de retorno testado; o arquivo privado é uma cópia de recuperação; reconstruir código antigo não garante gerar os mesmos bytes.

Para recuperar uma etapa interrompida, mantenha as escritas controladas e consulte os snapshots privados. No Docker, o arquivo `docker-source.json` contém a imagem antiga, o mesmo volume e os mesmos Secrets:

```bash
bash docker-lab/scripts/compose.sh -p docker-lab -f CAMINHO_PRIVADO/docker-source.json up -d --no-build --no-deps --wait api
```

Esse retorno muda apenas a API. Depois de um rollback definitivo, atualize também o Compose padrão para o destino escolhido antes de voltar aos comandos habituais. Um `up` padrão reaplica o digest declarado no repositório.

No Kubernetes, pause temporariamente a automação da Application, selecione a imagem anterior com a política de pull apropriada e confira o rollout, os dados e o tracing. A imagem instrumentada local exige recarregá-la com kind caso tenha saído do cache. Atualize a fonte Git antes de reativar self-heal; caso contrário, o Argo devolverá a API ao digest adotado. Não há rollback de PostgreSQL necessário para esses dois binários de API, pois o schema permanece compatível. Se uma versão futura fizer migração destrutiva, esse procedimento deixa de ser suficiente.

## Como a configuração foi alinhada

O Compose padrão usa o digest básico aprovado, sem construir outra imagem implicitamente. O `docker-lab/Dockerfile` também passa a descrever a versão Alpine para builds explícitos de desenvolvimento. Isso não altera a identidade da imagem publicada. Os manifestos de API e do Job de schema, tanto no Kubernetes lab quanto na base GitOps, usam a básica Alpine. O overlay `notes-traced` e o patch do tracing usam a derivada publicada com `IfNotPresent`, em vez de depender de um nome local com `Never`.

`tracing-lab/config/app-image.json` registra a imagem publicada, sua base e um fingerprint separado dos fontes para builds locais. `scripts/build.sh` prepara a imagem publicada por padrão; `--local` constrói e carrega outra tag, sem sobrescrever o digest de produção do lab nem implantá-la automaticamente. O hash dos fontes locais não é apresentado como prova de que um rebuild será idêntico à publicação.

O comando de remoção da infraestrutura de tracing agora recusa apagar Tempo/Collector enquanto houver Deployments ativos em notes-lab exportando para eles, incluindo a demonstração alternativa. Para desligar essa infraestrutura, restaure primeiro a aplicação pela fonte Git e pare as demonstrações instrumentadas.

O self-heal foi pausado somente durante os ensaios no estado vivo. Depois publicamos a configuração definitiva no argocd-lab, reativamos a política original com prune=false/selfHeal=true e conferimos a reconciliação. O arquivo de configuração de origem e os relatórios do ensaio ficam preservados.

## Achados visíveis e limites

Os alvos ativos passam a ser `notes-api`, `notes-api-otel` e `postgres`, todos com os digests Alpine já analisados. O alvo `notes-api-debian` preserva a API básica de retorno e seus **164 achados/44 HIGH**; `postgres-bookworm` continua preservando os achados da recuperação Debian do banco. A derivada instrumentada antiga também foi analisada localmente na íntegra, sem excluir seu inventário.

A mesma política continua bloqueando HIGH/CRITICAL, inclusive sem correção. Não adicionamos regras de ignore, não reduzimos severidades e não apagamos os relatórios anteriores. A cobertura dos advisories muda entre distribuições; zero achados na fotografia atual não garante ausência de vulnerabilidades futuras.

## Reproduzir em uma cópia ainda não adotada

O helper da operação atende estes checkouts irmãos e o cluster local existente, com as contas já endurecidas. Não é uma ferramenta genérica de deploy. Execute a partir da pasta do portfólio, antes de trocar os runtimes:

```bash
python3 security-lab/scripts/adopt-api.py snapshot
python3 security-lab/scripts/adopt-api.py docker
python3 security-lab/scripts/adopt-api.py kubernetes
```

Snapshots existentes e uma origem já adotada são recusados; não repita o ensaio sobre os labs prontos. A imagem anterior de tracing precisa estar carregada para o retorno. As etapas interrompem em erro, preservando backups e dados; no Kubernetes, deixam a automação pausada até a recuperação/publicação da configuração correta. Depois publique os manifests e restaure a política original do Argo. Este fluxo deve ocorrer com apenas um operador alterando os labs.

As evidências públicas estão em [api-adoption](../evidence/api-adoption); os dumps e conteúdos das notas permanecem privados. A demonstração experimental de 8016 é separada dos principais em 8000 e 8005. O lab de publicação e sua demonstração GHCR continuam como registros de uma versão anterior fixada; não foram atualizados silenciosamente nesta adoção.

## Resultado observado nesta adoção

Os dois bancos estavam vazios antes do ensaio. Para testar escritas reais, criamos notas Unicode depois da troca e conferimos todos os campos no rollback e no retorno ao Alpine. Isso demonstra preservação dessas escritas controladas; não simula uma base grande de produção.

Houve um timeout de leitura de `/notes` logo após o rollout da imagem instrumentada anterior. A operação parou preservando o backup e a nota; retomamos a conferência sem repetir o POST. O helper agora repete somente leituras em falhas transitórias. Os 19 testes de tracing passaram tanto na versão anterior quanto na Alpine adotada.

Também passaram os 23 testes da aplicação Docker, os 20 testes de banco e recursos e o ensaio de self-heal com preservação de nota e PVC. Os testes posteriores de ciclo de vida recriam containers Docker intencionalmente, mantendo o volume; a identidade do container foi preservada durante a troca de imagem da API em si. O arquivo privado da imagem antiga foi salvo com checksum; não ensaiamos sua recarga, e o rollback real utilizou a imagem já disponível nos nós.
