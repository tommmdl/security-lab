# Uma alternativa PostgreSQL com a correção da libxml2

Português · [English](postgres-alternative.en.md)

Esta página registra o teste isolado anterior. O Alpine agora foi adotado nos dois labs: [implantação atual e rollback](postgres-adoption.md).

A alternativa testada é PostgreSQL 17.11 sobre Alpine 3.24.2, com nosso gosu estático corrigido, os scripts existentes de separação de contas e zlib 1.3.2-r1. Ela traz libxml2 2.13.9-r2 e mantém a funcionalidade XML. A CVE-2026-6653 desaparece do relatório completo: a biblioteca foi substituída, não escondida do scanner.

O [aviso do Debian](https://security-tracker.debian.org/tracker/CVE-2026-6653) registra a correção na fonte a partir da libxml2 2.11.0, enquanto a versão Bookworm continua afetada. Conferimos a versão instalada no Alpine e a ligação dinâmica do servidor com libxml2. Passaram uma consulta XPath/XML inofensiva e os testes da aplicação. É evidência de versão/fornecedor e validação funcional, não reprodução de um exploit.

## O que apareceu nos scans

| Imagem/etapa | Achados | HIGH | CRITICAL |
|---|---:|---:|---:|
| Derivada Bookworm atual | 350 | 68 | 2 |
| Alpine oficial sem alterações | 61 | 24 | 1 |
| Alpine com o gosu corrigido | 1 MEDIUM | 0 | 0 |
| Candidata Alpine final, com zlib atualizada | 0 | 0 | 0 |

A imagem Alpine oficial corrige a libxml2 em questão, mas traz gosu compilado com Go 1.24.6, reintroduzindo CVE-2025-68121. O novo Dockerfile copia apenas nosso auxiliar estático da derivada Bookworm imutável. Não copia bibliotecas Debian. O achado médio restante era CVE-2026-85091 na zlib 1.3.2-r0; a atualização disponível 1.3.2-r1 o remove.

As quatro etapas continuam na [comparação](../evidence/postgres-alternative/comparison.json) e nos relatórios JSON completos ao lado dela. Usamos a mesma fotografia da base do Trivy 0.76.0 e a política mantida. Todas as severidades, achados sem correção e inventário permanecem habilitados; nenhuma exceção ou supressão VEX foi acrescentada. A imagem final passa no gate atual, mas zero achados reportados não prova segurança completa. Fornecedores de sistemas operacionais têm coberturas diferentes de avisos; as contagens não são uma classificação geral de distribuições.

## Preservar a origem antes de testar uma restauração

O Alpine usa musl/UID 70; o Bookworm existente usa glibc/UID 999. Não colocamos Alpine sobre um PGDATA ou PVC existente. Criamos projetos e volumes separados e usamos pg_dump/pg_restore em formato custom, seguindo a abordagem de [backup lógico do PostgreSQL](https://www.postgresql.org/docs/17/backup-dump.html).

O destino usa UTF8 com ICU/en-US. A origem usa libc/en_US.utf8. Os provedores e suas versões reais ficam no JSON dos testes. São ambientes de locale diferentes; o esquema de notas ordena por ID numérico e não tem índice sobre títulos. Testamos compatibilidade desta aplicação, não de índices de texto arbitrários, extensões ou consultas dependentes de locale. Veja a [documentação de locale](https://www.postgresql.org/docs/17/locale.html).

O teste reproduzível cria sete notas com português, japonês, emoji, aspas e acentos combinados. Depois da restauração lógica, compara todos os campos das linhas, propriedades das colunas, índices e estado da sequência. Confere um novo ID gerado, roda os 23 testes da API e os 20 de privilégios/recursos e verifica persistência após recriar os containers. Uma exportação reversa é restaurada em outro banco Debian: linhas e sequência atual coincidem, enquanto as linhas e a sequência da origem permanecem iguais.

A execução local também restaurou backups privados do Kubernetes, Docker e demonstração GHCR em outros três bancos no destino. Todos os campos das notas coincidiram. Os três bancos em execução estavam vazios; as sete notas controladas fornecem o caso com dados. Dumps e conteúdo de comparação ficam fora do Git. O resultado local tem 17 verificações controladas de migração mais essas três restaurações reais; o CI executa as 17 controladas, sem dados locais.

Contas e autenticação são recriadas pelo hook do lab, não por restauração indiscriminada dos objetos globais. A aplicação continua sem superusuário, a manutenção rejeita TCP e os limites de memória/CPU/PIDs são mantidos. O UID esperado do banco passa a 70 nesta imagem. A restauração com no-owner/no-acl e propriedade definida é específica ao esquema de notas; não afirmamos preservar toda possível permissão de um cluster.

## Ambiente de testes e ambiente padrão

A alternativa roda separadamente em http://localhost:8015. Ela contém sete notas controladas e usa seu próprio volume. Os três serviços originais e o PVC Kubernetes continuam com Bookworm. Os achados deles permanecem visíveis e bloqueando na matriz existente; isso não é uma troca de produção.

As [instruções do Docker lab](https://github.com/tommmdl/docker-lab/blob/main/docs/postgres-alternative.md) mostram como iniciar a demonstração isolada, repetir os testes e parar sem apagar o volume. O `scripts/alternative.sh` restringe as operações ao projeto alternativo; o teste cria e remove apenas seus próprios projetos de origem/destino. A demonstração local bem-sucedida fica separada.

O CI publica a mesma alternativa testada com tags `postgres-alpine-` no pacote público existente do GHCR. O consumo usa digest. A publicação não a liga aos volumes originais. Uma troca efetiva exigiria exportação final consistente, tratamento controlado das escritas, revisão de locale/índices/extensões e origem guardada para retorno; essa troca fica fora deste teste isolado.

Fontes: [tags oficiais](https://hub.docker.com/_/postgres), [Dockerfile Alpine](https://github.com/docker-library/postgres/blob/master/17/alpine3.24/Dockerfile), [registro da CVE no fornecedor](https://security-tracker.debian.org/tracker/CVE-2026-6653). Referências imutáveis das imagens e hashes dos relatórios acompanham as evidências.

## Publicada e conferida

O [GitHub Actions](https://github.com/tommmdl/github-actions-lab/actions/runs/39181777856) aprovou as 17 verificações de migração, 23 da API e 20 de segurança e publicou as imagens testadas. A alternativa do Compose fixa esse par de API/banco por digest. A análise completa obtida do GHCR também registra zero achados; os hashes dos manifests e digests de configuração conferem com as imagens testadas no CI. As [evidências de publicação e análise](https://github.com/tommmdl/security-lab/tree/main/evidence/postgres-alternative) ficam disponíveis na íntegra. É uma fotografia datada do scanner, sem garantia contra novos achados.

O [workflow de segurança](https://github.com/tommmdl/security-lab/actions/runs/39182367579) confirmou de forma independente **zero achados e gate aprovado para o Alpine**. Os 15 testes da política passaram. API e Bookworm continuam bloqueados; por isso a execução geral fica vermelha, como esperado. Os relatórios completos JSON/SARIF dos três alvos estão em [security-ci-reports](../evidence/postgres-alternative/security-ci-reports). Depois de atualizar somente a demonstração isolada para o par de imagens publicado, as sete notas continuaram idênticas; os dados originais e o PVC Kubernetes também foram conferidos sem alterações.
