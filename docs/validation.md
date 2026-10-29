# O que foi colocado à prova

[English](validation.en.md) · [Início](../README.md)

Os [15 testes locais](../evidence/local-tests.json) passaram. Treze usam relatórios sintéticos identificados como fixtures para testar os códigos de aprovação, bloqueio e erro: ausência de achados, severidade média, HIGH com e sem correção, CRITICAL, fim de suporte do sistema, inventário ausente, severidade inesperada, JSON inválido, arquivo inexistente, uma lista JSON no lugar de um relatório e uma coleção de achados com formato inválido.

Os outros dois testes executam Trivy config de verdade. O Dockerfile com USER root foi rejeitado por DS-0002; o exemplo com usuário não root e healthcheck passou no limiar HIGH/CRITICAL. Isso valida uma análise de configuração, não a remoção de vulnerabilidades da imagem base.

Também foram executados scans reais das duas imagens remotas, por digest e plataforma linux/amd64. Os dois comandos encerraram com código 1 porque os gates bloquearam os relatórios. JSON completo e SARIF foram gerados antes do bloqueio. Os [resumos locais](../evidence/local-summary.json) mostram as contagens; os diretórios notes-api e postgres em evidence guardam decisão, ocorrências bloqueadas e identificação da análise.

O Trivy terminou a coleta das duas imagens sem erro operacional. O bloqueio foi resultado da política: 48 ocorrências na API e 99 no PostgreSQL. Os achados têm dados da base utilizada no momento; este registro não afirma que são exploráveis pela aplicação, que houve incidente ou que foram corrigidos.

Não foram testados exploração, runtime reachability, autenticação em registry privado, Code Scanning, branch protection, varredura de secrets ou licenças. O scanner e seu arquivo de download foram fixados, mas a base de vulnerabilidades e o bundle de checks continuam atualizáveis. A integridade do arquivo do Trivy foi verificada por checksum; proveniência Sigstore não foi verificada.

A [execução final no GitHub Actions](https://github.com/tommmdl/security-lab/actions/runs/39173470418) aprovou os **15 testes do laboratório** e bloqueou as duas imagens: 48 ocorrências na API e 99 no PostgreSQL. Sua conclusão geral é **failure**, conforme a política. Veja os [testes](../evidence/ci-tests.json), o [resumo dos scans](../evidence/ci-summary.json) e os [jobs/revisão testada](../evidence/ci-run.json). Os hashes dos JSONs completos e a estrutura SARIF foram conferidos após baixar os artefatos. Os testes de configuração apagam os relatórios antigos e exigem um JSON recém-gerado antes de aceitar o código 1 esperado. Os commits posteriores de documentação não alteram o código testado.

## Ciclo real: vulnerabilidade nova depois da adoção

As imagens adotadas passaram no gate em 19/10/2026. Dez dias depois, sem mudança de imagem ou de código, a base de vulnerabilidades passou a reportar dois achados novos com correção publicada:

| Imagem adotada | Achado | Pacote | Correção |
| --- | --- | --- | --- |
| `postgres` (`sha256:8b6813ec…`) | CVE-2026-111943, HIGH | Go stdlib 1.27.2 no `gosu` | Go 1.27.3 |
| `notes-api-otel` (`sha256:e01c467c…`) | GHSA-6q48-6c7w-9gw2, CRITICAL | `certifi` 2026.7.22 | 2026.10.18 |

1. **Detecção.** O [run 40933751374](https://github.com/tommmdl/security-lab/actions/runs/40933751374), de 29/10/2026, foi o primeiro com a decisão esperada por imagem (`expect` em `config/targets.json`). As duas imagens Debian retidas foram bloqueadas como esperado, e as duas adotadas foram bloqueadas sem estar previstas, o que deixou o workflow vermelho. Os gates ficam em [`evidence/readopt/detected-postgres-gate-run-40933751374.json`](../evidence/readopt/detected-postgres-gate-run-40933751374.json) e [`detected-notes-api-otel-gate-run-40933751374.json`](../evidence/readopt/detected-notes-api-otel-gate-run-40933751374.json), porque os artefatos do Actions expiram em 30 dias.
2. **Correção na origem.** O `gosu` do PostgreSQL Alpine vinha copiado da imagem Debian retida. Agora o docker-lab o compila no próprio Dockerfile com `golang:1.27.3-bookworm` fixado por digest (commit `11223c7`). No tracing-lab, o `certifi` foi para 2026.10.18 (`3ced2dd`). A imagem Debian retida continua com o binário antigo e continua bloqueada.
3. **Rebuild pelo pipeline existente.** O github-actions-lab fixou as novas revisões (`5b49e2f`). O [run 40938591600](https://github.com/tommmdl/github-actions-lab/actions/runs/40938591600) testou e publicou o PostgreSQL Alpine `sha256:d99044c0…`, e o [run 40938591556](https://github.com/tommmdl/github-actions-lab/actions/runs/40938591556) testou e publicou a API OpenTelemetry `sha256:853f73da…`. Os dois scans locais deram ALLOW com zero HIGH/CRITICAL; `postgres-bookworm` seguiu BLOCK.
4. **Nova adoção com rollback no docker-lab.** O [`scripts/readopt-patched.py`](../scripts/readopt-patched.py) rodou no projeto Compose local:
   - [PostgreSQL](../evidence/readopt/postgres.json): 9 verificações. Pausa das escritas, backup lógico conferido numa base separada, troca de imagem no mesmo volume (mesma base PostgreSQL 17.11/Alpine 3.24; só o `gosu` mudou), escrita depois da troca, rollback real para a imagem anterior lendo essa escrita pela API e retorno à imagem corrigida. O `gosu` reportou go1.27.2 antes e go1.27.3 depois.
   - [API OpenTelemetry](../evidence/readopt/notes-api-otel.json): 6 verificações. Troca da imagem, CRUD, rollback real lendo a nota escrita na imagem nova e retorno. O `certifi` reportou 2026.7.22 e depois 2026.10.18. Os exporters OTLP ficaram desligados, porque o Compose não tem collector.
5. **Propagação.** Os novos digests foram para o docker-lab (`a4a2336`), o kubernetes-lab (`07d1df7`), o argocd-lab (`283b20f`) e o tracing-lab (`d0d2921`), além do `config/targets.json` deste repositório. Os CIs dos consumidores passaram: [tracing-lab 40942613603](https://github.com/tommmdl/tracing-lab/actions/runs/40942613603), em kind com traces reais, [kubernetes-lab 40942596923](https://github.com/tommmdl/kubernetes-lab/actions/runs/40942596923) e [argocd-lab 40942605890](https://github.com/tommmdl/argocd-lab/actions/runs/40942605890). O [run 40942678712](https://github.com/tommmdl/security-lab/actions/runs/40942678712) mostra o gate esperado para as cinco imagens.

Limites: o banco local do docker-lab não tinha notas próprias (as adoções de 19/10 também registraram zero linhas), então a comparação de linhas cobriu as duas notas de teste, removidas no fim. Os labs de backup, DR, failover e chaos mantêm os digests das execuções que documentam. O caminho Kubernetes da API OpenTelemetry foi validado pelo CI do tracing-lab, não por um rollback local em cluster.
