# O que existe por trás dos 44 HIGH da API

Português · [English](api-high-review.en.md)

Esta é a análise histórica do Debian. A API ativa agora é Alpine; a imagem afetada fica preservada como `notes-api-debian`. [Adoção atual](api-adoption.md).

A nova análise completa da imagem `sha256:343f2b23294c09bea9c3250a3b3fd1f95d817acea9db0231dfaaaf406f22fbac` confirmou **164 achados, dos quais 44 HIGH, distribuídos em oito CVEs distintas**. Esses 44 são ocorrências de pacote/CVE: um mesmo problema do pacote-fonte util-linux aparece em vários pacotes binários. Nenhum dos HIGH desta fotografia foi atribuído a Flask, Gunicorn ou Psycopg.

A decisão continua **block**. Não alteramos severidades, ignorefile, política, metadados do dpkg nem os relatórios históricos. As medidas desta rodada limitam exposição e impacto; não corrigem os binários Debian afetados e não aprovam a imagem.

## A análise de cada CVE

| CVE | Ocorrências HIGH | O caminho afetado e a situação no lab |
| --- | ---: | --- |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) | 9 | Hooks privilegiados de mount após falha de um auxiliar. `mount` existe e mantém SUID; a API não recebe privilégios para montar e a tentativa benigna foi negada. |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) | 9 | Descritor privilegiado herdado por `nsenter --join-cgroup`. Não há operador privilegiado usando esse caminho pela API; a entrada benigna no namespace foi negada. |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) | 9 | Resolução de symlink em `X-mount.subdir`, com pré-requisitos de kernel/fstab. Não há montagem autorizada pela aplicação. Não dependemos da versão atual do kernel como proteção permanente. |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) | 9 | Redirecionamento de origem em bind mounts restritos. A API não faz essas operações e não tem a capability necessária. |
| [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369) | 1 | Funções de caminho do libacl usadas por um chamador privilegiado. Não identificamos esse chamador nos endpoints de notas; o processo é comum e o rootfs é somente leitura. Isso não corrige a biblioteca. |
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) | 4 | Overflow na ferramenta `infocmp`. O executável está presente; não é uma conclusão de ausência. Os endpoints não o executam nem recebem arquivos terminfo. |
| [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) | 2 | Problema no serviço `systemd-homed`. Há bibliotecas systemd/udev, mas o binário específico não está instalado e o serviço não roda na API. O achado de pacote-fonte permanece. |
| [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538) | 1 | Exaustão de memória em `Archive::Tar`. `perl-base` está instalado, mas importar o módulo falha. Não há endpoint de upload/extrator de arquivos. Mantemos o alerta. |

A lista de todos os pacotes e versões está em [triage.json](../evidence/api-high-review/triage.json). A inferência sobre exposição vem da inspeção da imagem, dos endpoints e dos testes benignos; não equivale a demonstrar que qualquer exploração futura é impossível. A imagem de tracing deriva da API básica, mas tem componentes adicionais: os testes de seus controles não substituem um scan completo próprio dessa derivada.

## O que já tem correção e por que não fizemos uma troca cega

As fontes acima registram correções upstream/em versões mais novas: util-linux 2.42.3/2.42.4, acl 2.4.0, ncurses em ramo posterior, systemd em versões posteriores e Archive::Tar 3.10. Isso não significa que esses reparos tenham chegado ao Trixie instalado.

Consultamos os repositórios Trixie e Trixie-security dentro de um container descartável, depois de atualizar o índice do apt. Para os cinco grupos, o candidato continua igual à versão instalada. O [registro da consulta](../evidence/api-high-review/stable-package-candidates.txt) e os trackers deixam essa diferença explícita. Nesta fotografia, nenhum dos 44 HIGH tem FixedVersion indicada pelo Trivy para essa distribuição.

Misturar pacotes sid/forky no runtime estável não foi tratado como atualização segura. Algumas mudanças envolvem ABI. Também não forçamos a remoção de pacotes Essential como util-linux, ncurses-bin e perl-base: isso pode quebrar a imagem e suas ferramentas de manutenção. `infocmp` e os utilitários de mount continuam reconhecidos nas evidências; não apagamos inventário para reduzir números.

Uma base menor ou outra distribuição pode ser ensaiada depois, com instalação real de todas as dependências, scanner com inventário completo e testes da API e do OpenTelemetry. Esse ensaio não foi realizado aqui e não é apresentado como uma correção pronta.

## O que mudou de verdade

O Compose passa a limitar a API a **256 MiB, uma CPU e 128 processos**. O `/tmp` fica em tmpfs de **64 MiB**, com noexec, nosuid e nodev. Permanecem UID/GID 10001, todas as capabilities removidas, no-new-privileges e rootfs somente leitura. A API é publicada somente em localhost; não recebe socket Docker nem volumes do host da aplicação.

No Kubernetes, o limite de memória de 256 MiB e o emptyDir em memória de 64 MiB já existiam. Acrescentamos **limite de uma CPU por container da API** nos manifests básicos e na fonte do Argo CD. UID/GID 10001, seccomp RuntimeDefault, allowPrivilegeEscalation=false, capabilities vazias e ausência de token de ServiceAccount continuam ativos. Não foi criado um limite de PIDs por container no manifesto Kubernetes; o valor efetivo observado fica no relatório. Também não afirmamos que o emptyDir Kubernetes ganhou noexec.

Limitar recursos reduz o impacto de consumo excessivo, sem garantir disponibilidade contra DoS. A configuração de segurança precisa acompanhar a imagem: executar o mesmo digest com opções privilegiadas invalidaria parte importante desta análise. Não há patch nem reconstrução da imagem nesta rodada; houve ajuste e validação do runtime. Banco, credenciais e volumes não foram trocados.

## Como conferimos

`tests/api_runtime.py` verifica os processos reais de Docker e Kubernetes, os valores dos cgroups, a recusa de escrita no rootfs, a recusa de mount e nsenter, a ausência de systemd-homed/Archive::Tar e a rejeição HTTP 413 para corpo maior que 4 KiB. Ele não usa payload de exploração, arquivo terminfo malformado ou bomba de memória.

```bash
python3 scripts/scan.py notes-api-debian     # código 1 esperado: bloqueada
python3 scripts/triage-api.py
python3 tests/api_runtime.py          # requer os checkouts irmãos e os dois labs ativos
```

Execute o teste de runtime sem outro teste de ciclo de vida da API em paralelo. O scanner remoto e a triagem podem rodar sem Docker/cluster, usando o relatório disponível. Os testes sintéticos da política continuam separados dos controles vivos e da análise de vulnerabilidades.

Os [relatórios completos, testes e limites](../evidence/api-high-review) preservam a fotografia antes/depois. Uma redução de exposição não foi convertida em redução artificial de achados: os 44 HIGH continuam visíveis e bloqueando.

Validação registrada: passaram **16 verificações de runtime no Docker, 13 no Kubernetes e 23 de integração da API**. Os cgroups Docker mostraram 256 MiB, quota de CPU 100000/100000 e 128 PIDs. No Kubernetes, 256 MiB e quota 100000/100000; o limite de PIDs já existente observado está registrado sem atribuí-lo a uma alteração de manifesto. O scan completo posterior à mitigação continua com 164 achados/44 HIGH e decisão block.

A API instrumentada também passou nos 19 testes de tracing depois do rollout do limite de CPU. Os 15 testes da política passaram separadamente. O registro de implantação confirma que a imagem Docker corresponde ao digest analisado, a derivada de tracing permanece igual e o Argo está Synced/Healthy com self-heal ativo.

O [workflow de segurança](https://github.com/tommmdl/security-lab/actions/runs/39249785138) reproduziu o resultado: 15 testes da política passaram, a API continuou bloqueada pelos 44 HIGH, o PostgreSQL Alpine ativo passou e o Bookworm guardado permaneceu bloqueado. O [workflow Kubernetes](https://github.com/tommmdl/kubernetes-lab/actions/runs/39249676675) passou nos 24 testes funcionais de recuperação, persistência e rollback depois do limite de CPU. Os relatórios completos JSON/SARIF da API no CI estão preservados junto dos locais.
