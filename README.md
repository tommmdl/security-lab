# Antes de aprovar uma imagem

[English](README.en.md) · Português

Os outros laboratórios mostram a aplicação funcionando. Aqui a pergunta muda: o que existe dentro da imagem que merece atenção antes de ela seguir no pipeline?

O Trivy analisa três imagens por digest: a API básica, o PostgreSQL Bookworm usado nos labs e uma alternativa Alpine testada em separado. O GitHub Actions guarda os relatórios e bloqueia a etapa se a política encontrar ocorrências HIGH ou CRITICAL, inclusive sem correção publicada.

## Uma alternativa testada para a libxml2

A alternativa Alpine ficou com **zero achados na análise completa registrada**. Passaram os testes de restauração lógica, API, segurança e retorno ao Debian; os bancos originais continuam intactos. Os gates da API e do Bookworm seguem bloqueados. Veja a [comparação e as evidências completas](docs/postgres-alternative.md).

## Análise dos críticos restantes do PostgreSQL

SQLite e ferramentas GPG sem uso foram removidos da imagem publicada. O PostgreSQL passa de 412 para **350 achados**, com **68 HIGH e 2 CRITICAL** restantes. A libxml2 recebe controles compensatórios e continua afetada; o binário zlib do Debian não compila o MiniZip afetado, mas o alerta continua visível e bloqueando. Veja a [análise, as fontes e as evidências completas](docs/postgresql-critical.md).

## Depois da primeira rodada de correções

A API passou de 173 para 164 achados; o PostgreSQL, de 472 para 412. Não restaram achados com correção indicada nessa fotografia da base. Ainda há **44 HIGH na API e 71 HIGH + 3 CRITICAL no banco**, por isso as duas imagens continuam bloqueadas. Os [relatórios completos e a comparação](docs/remediation.md) mostram o que mudou e o que falta tratar.

## O resultado inicial, preservado

Na execução local registrada, a API foi bloqueada por **48 ocorrências HIGH**. O PostgreSQL foi bloqueado por **95 HIGH e 4 CRITICAL**. Essas contagens são ocorrências de pacote/CVE, não necessariamente vulnerabilidades distintas: os conjuntos bloqueados têm 12 e 49 identificadores distintos, respectivamente.

Os **15 testes do laboratório passaram**, incluindo um Dockerfile que o Trivy rejeita e outro que passa na análise de configuração. Isso não aprova as imagens: o job de testes e os gates de imagem têm resultados separados. O workflow completo deve ficar vermelho enquanto as imagens violarem a política.

Veja os [resultados e o que foi testado](docs/validation.md) e a [triagem dos achados](docs/triage.md).

O [GitHub Actions](https://github.com/tommmdl/security-lab/actions/runs/39173470418) reproduziu esse resultado: **15 testes aprovados e as duas imagens bloqueadas**.

## Rodar localmente

Use Linux x86_64 ou WSL, Git, Python 3 e curl, com acesso ao GitHub, aos registries e à base de vulnerabilidades. Para estes alvos remotos, não é necessário acesso ao socket Docker nem ao cluster Kubernetes.

```bash
python3 scripts/prepare.py
python3 tests/verify.py
python3 scripts/scan.py notes-api
python3 scripts/scan.py postgres
python3 scripts/scan.py postgres-alpine
```

Cada comando de scan pode encerrar com código 1 porque a imagem foi bloqueada. Execute os alvos separadamente ou use terminais separados; não coloque `|| true` num pipeline de aprovação. O cache local do Trivy pode serializar acessos concorrentes.

O Trivy v0.76.0 fica em `.local/bin`. O instalador verifica o SHA-256 do arquivo oficial contra o valor versionado em `config/tool.json`; não executa um instalador remoto via pipe. A verificação cobre a integridade desse arquivo, sem substituir uma verificação de proveniência Sigstore. O cache também fica em `.local/`, ignorado pelo Git.

## O que faz a decisão

A política está em `config/policy.json`:

- HIGH e CRITICAL bloqueiam, com ou sem versão corrigida disponível.
- Um sistema operacional identificado como fora de suporte também bloqueia.
- Relatório ausente, inválido ou sem inventário de pacotes não vira aprovação.
- Não há CVEs suprimidos; `config/empty.ignore` fica sem exceções.

Primeiro o Trivy coleta um JSON completo, com todas as severidades e os pacotes. Nessa etapa `--exit-code 0` permite terminar a coleta e gerar SARIF. Depois `gate.py` aplica a política e seu resultado é o código final de `scan.py`. O código zero da coleta não é o resultado de segurança.

| Código do avaliador | Significado |
| --- | --- |
| 0 | A imagem passou pelos critérios desta política. Não significa ausência de vulnerabilidades. |
| 1 | O relatório foi analisado e a política bloqueou a imagem. |
| 2 | O relatório ou a configuração do avaliador é inválido. |

Falhas de rede, banco de vulnerabilidades ou scanner também fazem o comando falhar. Nesse caso pode não existir `gate.json`. Um novo scan apaga seus relatórios anteriores antes de começar, para não apresentar um resultado antigo como atual.

## Ler os arquivos

Os resultados locais ficam em `.local/reports/notes-api/` e `.local/reports/postgres/`:

| Arquivo | Para que serve |
| --- | --- |
| `scan.json` | Relatório completo do Trivy, com pacotes, versões, fontes e achados. |
| `scan.sarif` | O mesmo resultado convertido para ferramentas que aceitam SARIF. |
| `gate.json` | Decisão e lista de ocorrências bloqueadas. |
| `run.json` | Imagem, plataforma, versão da ferramenta, metadata da base e hash do relatório. |

SARIF é publicado como artefato; este projeto não o envia automaticamente ao GitHub Code Scanning. Nenhuma permissão `security-events: write`, token de registry privado ou segredo adicional é necessário.

As imagens estão fixadas em `config/targets.json`, mas a base de vulnerabilidades continua sendo atualizada. Uma nova execução pode ter contagens diferentes sem mudar a imagem ou o código. Os registros incluem a data de atualização e download da base. Eles são retratos do momento da análise.

## O caminho no GitHub Actions

Em push de código/configuração para main, pull request e execução manual, o workflow:

1. Baixa e verifica a versão fixada do Trivy.
2. Testa aprovação, bloqueio, erro de relatório e os dois Dockerfiles de exercício.
3. Analisa API e banco em jobs separados, sem cancelar um quando o outro falha.
4. Guarda JSON, SARIF e a decisão mesmo quando há bloqueio.

As actions de checkout e upload estão fixadas por commit. O token do workflow tem apenas leitura do conteúdo. Não há `continue-on-error` nos gates. O workflow não publica imagens e não altera a aplicação que já está rodando.

Para usar a mesma ideia antes de publicar uma imagem em outro projeto, coloque o scan antes do push e faça a publicação depender do job de aprovação. O gate daqui não configura proteção de branch nem bloqueia automaticamente o pipeline de outro repositório.

## Um exercício pequeno de configuração

```bash
.local/bin/trivy config --severity HIGH,CRITICAL --exit-code 1 fixtures/dockerfiles/unsafe
.local/bin/trivy config --severity HIGH,CRITICAL --exit-code 1 fixtures/dockerfiles/improved
```

O primeiro Dockerfile define USER root e é rejeitado pelo check DS-0002. O segundo usa o usuário não root já existente na mesma imagem e declara um healthcheck. Os testes verificam o primeiro retorno 1 e o segundo retorno 0. Eles não constroem nem executam esses Dockerfiles.

Essa melhoria de configuração não corrige os pacotes da imagem base. A análise de Dockerfile e a análise de vulnerabilidades da imagem respondem a perguntas diferentes.

## O que ficou fora deste primeiro lab

Os alvos são a imagem básica da API e a imagem do banco. A variante local instrumentada do tracing-lab não faz parte desta matriz do CI; ela foi analisada separadamente na rodada de correções, com os relatórios completos em `evidence/remediation/traced-api-*.json`. O scan usa somente vulnerabilidades conhecidas do inventário suportado pelo Trivy; não testa exploração, alcance em runtime, secrets, licenças ou toda a configuração do cluster.

Um achado precisa de triagem. Caminho do arquivo, pacote, versão, fonte do aviso, correção e uso real ajudam a avaliar o impacto. Não há alteração automática das imagens ou exceção inventada para deixar o resultado verde.

Os relatórios completos da rodada de correções ficam em `evidence/remediation/`, além dos artefatos do CI. A análise inicial não reiniciou containers; a atualização das imagens tem testes e registros próprios. Configuração, testes e registros feitos com ajuda do assistente.

Referências: [release fixada](https://github.com/aquasecurity/trivy/releases/tag/v0.76.0), [análise de imagens](https://trivy.dev/docs/latest/guide/target/container_image/), [vulnerabilidades e severidades](https://trivy.dev/docs/latest/guide/scanner/vulnerability/) e [integração com CI](https://trivy.dev/docs/latest/ecosystem/cicd/).

A [primeira rodada de correções](docs/remediation.md) compara os relatórios completos de antes e depois. As duas imagens ainda são bloqueadas pelo gate mantido.
