# O que foi colocado à prova

[English](validation.en.md) · [Início](../README.md)

Os [13 testes locais](../evidence/local-tests.json) passaram. Onze usam relatórios sintéticos identificados como fixtures para testar os códigos de aprovação, bloqueio e erro: ausência de achados, severidade média, HIGH com e sem correção, CRITICAL, fim de suporte do sistema, inventário ausente, severidade inesperada, JSON inválido e arquivo inexistente.

Os outros dois testes executam Trivy config de verdade. O Dockerfile com USER root foi rejeitado por DS-0002; o exemplo com usuário não root e healthcheck passou no limiar HIGH/CRITICAL. Isso valida uma análise de configuração, não a remoção de vulnerabilidades da imagem base.

Também foram executados scans reais das duas imagens remotas, por digest e plataforma linux/amd64. Os dois comandos encerraram com código 1 porque os gates bloquearam os relatórios. JSON completo e SARIF foram gerados antes do bloqueio. Os [resumos locais](../evidence/local-summary.json) mostram as contagens; os diretórios notes-api e postgres em evidence guardam decisão, ocorrências bloqueadas e identificação da análise.

O Trivy terminou a coleta das duas imagens sem erro operacional. O bloqueio foi resultado da política: 48 ocorrências na API e 99 no PostgreSQL. Os achados têm dados da base utilizada no momento; este registro não afirma que são exploráveis pela aplicação, que houve incidente ou que foram corrigidos.

Não foram testados exploração, runtime reachability, autenticação em registry privado, Code Scanning, branch protection, varredura de secrets ou licenças. O scanner e seu arquivo de download foram fixados, mas a base de vulnerabilidades e o bundle de checks continuam atualizáveis. A integridade do arquivo do Trivy foi verificada por checksum; proveniência Sigstore não foi verificada.

O resultado no GitHub Actions será registrado depois da primeira execução.
