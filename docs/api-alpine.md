# Testando a API no Alpine antes de trocar o padrão

Português · [English](api-alpine.en.md)

Esta página registra o ensaio isolado anterior. O Alpine agora foi adotado nos labs principais: [implantação atual e rollback](api-adoption.md).

A alternativa mantém **Python 3.13.16 e o mesmo lock da aplicação**, mas troca Debian/glibc por Alpine 3.24.2/musl. Construímos duas imagens: a API básica e a derivada com OpenTelemetry. As duas registraram **zero achados no scan completo local**. A API Debian principal continua na imagem anterior, com seus 44 HIGH visíveis e bloqueando.

É um teste separado. O Docker usa projeto, porta e volume próprios; o Kubernetes usa outro Deployment, Service, banco e PVC. O Service principal não seleciona os Pods candidatos. Não montamos os volumes principais nas candidatas e não mudamos a fonte da aplicação principal no Argo CD.

## A primeira base também tinha achados

| Imagem/etapa | Total | HIGH | Outros achados |
| --- | ---: | ---: | --- |
| API Debian, referência preservada | 164 | 44 | 58 MEDIUM, 61 LOW, 1 UNKNOWN |
| Python Alpine oficial, antes da aplicação | 7 | 4 | 3 MEDIUM |
| Aplicação instalada, pip/ensurepip removidos | 1 | 0 | 1 MEDIUM na zlib |
| API Alpine com zlib atualizada | 0 | 0 | nenhum nesta fotografia |
| API Alpine com OpenTelemetry | 0 | 0 | nenhum nesta fotografia |

A imagem oficial tinha alertas nas dependências distribuídas com as ferramentas de instalação — msgpack, setuptools e urllib3 — além da zlib. Instalamos o lock e retiramos pip/ensurepip do runtime, como já era feito no Debian. O código e os metadados dessas ferramentas saem juntos; não apagamos o inventário do apk nem alteramos os metadados da aplicação. Depois atualizamos **zlib 1.3.2-r0 para 1.3.2-r1**, correção indicada para CVE-2026-85091. Os relatórios intermediários ficaram guardados.

O scanner manteve **40 entradas de inventário na API básica e 63 na instrumentada**, incluindo os pacotes do Alpine e os metadados Python. Os scans usam todas as severidades, incluem achados sem correção e passam pela mesma política. Nenhuma regra de ignore foi adicionada.

Os 44 HIGH do Debian não foram “corrigidos por atualização” dentro daquele Debian. A alternativa tem outro conjunto de pacotes e bibliotecas. Distribuições também têm coberturas diferentes de advisories; zero nessa base do Trivy não garante ausência de vulnerabilidades ou equivalência de cobertura. A [análise dos oito identificadores originais](api-high-review.md) e os relatórios completos continuam disponíveis.

## O ponto delicado: dependências nativas e tracing

Alpine usa musl. Não copiamos extensões glibc da imagem Debian: o build instala **somente wheels compatíveis com o ambiente**, usando `--only-binary=:all:`. Se uma versão não tiver wheel compatível, o build falha em vez de compilar silenciosamente outra combinação.

Psycopg 3.3.6 carregou o backend binário musllinux e o libpq 18.6, conectando ao PostgreSQL 17.11 do lab. As duas variantes passaram em **23 testes da API e 20 de segurança SQL/recursos cada**, incluindo escrita, leitura, erro 503 com o banco parado e persistência após recriar containers. Testes separados conferiram sete títulos Unicode, com português, japonês, emoji, aspas e acentos combinados, removendo somente as próprias notas.

A derivada instala o lock OpenTelemetry em um estágio Alpine com a mesma base da API; depois copia essas dependências e o mesmo `traced.py`. O pipeline portátil exercita **13 verificações reais de Flask/Psycopg → Collector → Tempo**, sem injetar spans sintéticos. No cluster existente, a candidata passou nos **19 testes completos**, incluindo parent/child dos spans, SELECT, escrita, 404, privacidade do título, consulta pelo Grafana e correlação com Loki.

Para a correlação funcionar, o Alloy passa a aceitar também o label `notes-api-alpine`, no namespace em que já tem permissão. Não ampliamos o RBAC. A aplicação principal continua com `notes-api`. O teste de tracing aceita o Service, nome de serviço e label candidatos por ambiente; os padrões continuam iguais aos do lab original.

O primeiro startup mostrou uma corrida com a inicialização do banco de teste. Acrescentamos um initContainer que espera uma conexão SQL antes de iniciar a API. Ele herda as restrições de segurança e os limites do workload. O ensaio final foi repetido depois desse ajuste.

## Como repetir

Build da API a partir de docker-lab:

```bash
docker build -f images/api-alpine/Dockerfile -t docker-lab-api-alpine:local .
```

Build da instrumentação a partir de tracing-lab:

```bash
docker build -f instrumentation/Dockerfile.alpine -t docker-lab-api-alpine-otel:local instrumentation
```

A máquina precisa de Docker com BuildKit/Buildx para construir as imagens. A base está fixada por digest; os locks mantêm as versões da aplicação e do tracing. Os testes atendem **linux/amd64**; outras arquiteturas não foram certificadas.

```bash
# docker-lab: cria e remove somente projetos temporários próprios
python3 tests/api_alpine.py

# tracing-lab: stack Compose descartável, com Collector e Tempo reais
python3 tests/alpine_otlp.py
```

Para o cluster local já preparado, carregue a imagem local com kind ou use o digest publicado, depois:

```bash
python3 scripts/alpine-lab.py up
python3 scripts/alpine-lab.py test
python3 scripts/alpine-lab.py status
```

Esse helper requer kubernetes-lab como checkout irmão, o Secret existente de notas e a infraestrutura de observabilidade. Ele cria `notes-api-alpine`, `api-alpine-db` e PVC `data-api-alpine-db-0`, com selectors próprios. Recusa substituir recursos que não tenham seu label de propriedade. `down` remove somente esses workloads/Services e **preserva o PVC**. Ele não cria nem altera a Application principal do Argo CD.

## Demonstração e decisão

O Docker tem uma demonstração isolada em **http://localhost:8016**:

```bash
bash scripts/api-alpine.sh up -d --no-build --wait
bash scripts/api-alpine.sh ps
bash scripts/api-alpine.sh down
```

O wrapper fixa o projeto alternativo e recusa builds pelo Compose para não construir acidentalmente o Dockerfile Debian. `down` preserva seu volume. A demonstração principal continua em 8000; o Kubernetes principal continua em 8005. Os limites de recursos, UID não root, capabilities removidas, rootfs somente leitura e no-new-privileges acompanham a candidata.

A publicação usa um workflow separado no github-actions-lab: constrói as duas imagens, testa aplicação/SQL/OTLP, faz scan completo e aplica o gate antes de publicar. As identidades são conferidas antes e depois do pull por digest. As tags usam `api-alpine-` e `api-alpine-otel-`; não substituem os pins principais. Os relatórios das imagens publicadas ficam ao lado dos locais.

Este ensaio não adota a alternativa nos labs principais nem prova compatibilidade geral de extensões nativas. Uma adoção posterior precisaria trocar os pins de forma controlada, validar observabilidade e conservar o retorno à imagem anterior. Como a troca aqui é só de API e os bancos de teste são separados, não houve migração de dados dos bancos principais.

Veja [todos os relatórios, comparações e testes](../evidence/api-alpine). Referências: [imagem Python oficial](https://hub.docker.com/_/python) e [instalação do Psycopg](https://www.psycopg.org/psycopg3/docs/basic/install.html). A compatibilidade relatada acima vem da execução real, não apenas da documentação.

## Publicadas e conferidas

O [workflow de publicação](https://github.com/tommmdl/github-actions-lab/actions/runs/39260441607) passou em **23 testes da API + 20 de SQL/segurança para cada variante**, 13 de OTLP/Tempo e nos gates completos das duas imagens. Buscamos os manifests do registry de forma independente e verificamos seus hashes; os digests de configuração conferem com os IDs testados no CI. As [referências publicadas](../evidence/api-alpine/published-images.txt), a [verificação do registry](../evidence/api-alpine/registry-verification.json) e os scans locais/CI/remotos completos ficaram guardados. As duas análises remotas também registraram zero achados. A matriz de segurança acompanha as duas candidatas separadamente, mantendo o alvo Debian principal.

O [workflow de segurança com cinco imagens](https://github.com/tommmdl/security-lab/actions/runs/39261269696) aprovou de forma independente as duas candidatas publicadas, com zero achados. Os 15 testes da política e o gate do PostgreSQL ativo passaram; a API Debian segue bloqueada pelos 44 HIGH e o Bookworm guardado também continua bloqueado. Por isso a execução geral fica vermelha, como esperado. Os JSON/SARIF completos de todos os alvos estão em [security-matrix-reports](../evidence/api-alpine/security-matrix-reports). A derivada instrumentada publicada também passou nos 19 testes vivos de tracing; as duas demonstrações publicadas preservaram sete títulos Unicode cada. Conferimos os processos candidatos reais: UID/GID 10001, capabilities efetivas vazias, no-new-privileges e seccomp ativos.
