# Transformar o relatório em trabalho concreto

[English](triage.en.md) · [Início](../README.md)

O gate é conservador. Ele para a aprovação e deixa um relatório para investigar. Severidade vem das fontes usadas pelo Trivy; exploração possível, alcance da aplicação e prioridade operacional exigem outra análise.

## O que apareceu na análise local

| Imagem | HIGH | CRITICAL | Ocorrências bloqueadas sem correção publicada |
| --- | ---: | ---: | ---: |
| API básica | 48 | 0 | 44 |
| PostgreSQL | 95 | 4 | 74 |

Na API, quatro ocorrências HIGH tinham FixedVersion preenchido no relatório: msgpack 1.1.2 → 1.2.1, setuptools 70.3.0 → 78.1.1 e dois avisos de urllib3 2.7.0 → 2.8.0. Essas são versões informadas pelo scanner, não uma atualização já aplicada ou testada neste projeto. Confira o caminho e os avisos do pacote antes de alterar a aplicação.

No PostgreSQL, parte dos achados está em `usr/local/bin/gosu`, um executável com bibliotecas Go embutidas. Os outros achados incluem pacotes do Debian. Uma ocorrência no helper não significa que o servidor PostgreSQL foi escrito em Go. Atualizar uma ferramenta Go instalada separadamente não reconstrói esse executável.

Os quatro achados CRITICAL locais são CVE-2025-7458 em libsqlite3-0, CVE-2026-6653 em libxml2, CVE-2023-45853 em zlib1g e CVE-2025-68121 na stdlib do helper gosu, segundo o relatório. Use Target, versão, Status, fontes e referências do JSON para investigar cada um; não trate todas as ocorrências como o mesmo caminho de exploração.

## Um roteiro de triagem

1. Confirme o digest e a plataforma no run.json. Uma tag nova pode apontar para outra imagem.
2. Agrupe por identificador e pacote. Um CVE pode afetar vários pacotes derivados da mesma origem.
3. Abra o Target e os dados de pacote no scan.json. Diferencie biblioteca Python, pacote do sistema e código Go embutido num binário.
4. Confira FixedVersion, Status e os links do fornecedor. Campo vazio não é garantia de que a distribuição esteja sem manutenção; pode haver decisões específicas do fornecedor.
5. Prepare uma mudança de imagem base ou dependência num branch do projeto responsável. Rebuild e testes funcionais vêm antes de promover o novo digest.
6. Repita o scan da imagem construída e compare os relatórios. Fixar uma versão em requirements sem reconstruir a imagem não muda o artefato antigo.

Nenhuma dessas atualizações foi implantada pelo security-lab. Ele registra os alvos existentes e bloqueia sua aprovação segundo a política escolhida.

## Se uma exceção for necessária em outro contexto

Uma decisão de aceitar risco precisa de responsável, justificativa ligada ao aviso/pacote, escopo, evidência e prazo de revisão. Este laboratório não tem exceções aprovadas. Por isso o arquivo de ignore continua vazio, mesmo para achados sem FixedVersion.

## Por que dois resultados podem divergir

O JSON completo também lista LOW, MEDIUM e UNKNOWN; o gate decide sobre HIGH/CRITICAL e fim de suporte do sistema. Fontes podem classificar a mesma vulnerabilidade de forma diferente, e a base muda com o tempo. Compare a metadata da base antes de interpretar uma diferença de contagem como mudança na imagem.

A imagem básica e a instrumentada são artefatos distintos. Repetir o scan da base não mede automaticamente todas as bibliotecas adicionadas pelo tracing-lab. Para ampliar a matriz, publique um alvo apropriado e adicione seu digest ao config/targets.json e ao workflow.
