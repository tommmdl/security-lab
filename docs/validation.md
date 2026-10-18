# O que foi colocado à prova

[English](validation.en.md) · [Início](../README.md)

Os [15 testes locais](../evidence/local-tests.json) passaram. Treze usam relatórios sintéticos identificados como fixtures para testar os códigos de aprovação, bloqueio e erro: ausência de achados, severidade média, HIGH com e sem correção, CRITICAL, fim de suporte do sistema, inventário ausente, severidade inesperada, JSON inválido, arquivo inexistente, uma lista JSON no lugar de um relatório e uma coleção de achados com formato inválido.

Os outros dois testes executam Trivy config de verdade. O Dockerfile com USER root foi rejeitado por DS-0002; o exemplo com usuário não root e healthcheck passou no limiar HIGH/CRITICAL. Isso valida uma análise de configuração, não a remoção de vulnerabilidades da imagem base.

Também foram executados scans reais das duas imagens remotas, por digest e plataforma linux/amd64. Os dois comandos encerraram com código 1 porque os gates bloquearam os relatórios. JSON completo e SARIF foram gerados antes do bloqueio. Os [resumos locais](../evidence/local-summary.json) mostram as contagens; os diretórios notes-api e postgres em evidence guardam decisão, ocorrências bloqueadas e identificação da análise.

O Trivy terminou a coleta das duas imagens sem erro operacional. O bloqueio foi resultado da política: 48 ocorrências na API e 99 no PostgreSQL. Os achados têm dados da base utilizada no momento; este registro não afirma que são exploráveis pela aplicação, que houve incidente ou que foram corrigidos.

Não foram testados exploração, runtime reachability, autenticação em registry privado, Code Scanning, branch protection, varredura de secrets ou licenças. O scanner e seu arquivo de download foram fixados, mas a base de vulnerabilidades e o bundle de checks continuam atualizáveis. A integridade do arquivo do Trivy foi verificada por checksum; proveniência Sigstore não foi verificada.

A [execução final no GitHub Actions](https://github.com/tommmdl/security-lab/actions/runs/39173470418) aprovou os **15 testes do laboratório** e bloqueou as duas imagens: 48 ocorrências na API e 99 no PostgreSQL. Sua conclusão geral é **failure**, conforme a política. Veja os [testes](../evidence/ci-tests.json), o [resumo dos scans](../evidence/ci-summary.json) e os [jobs/revisão testada](../evidence/ci-run.json). Os hashes dos JSONs completos e a estrutura SARIF foram conferidos após baixar os artefatos. Os testes de configuração apagam os relatórios antigos e exigem um JSON recém-gerado antes de aceitar o código 1 esperado. Os commits posteriores de documentação não alteram o código testado.
