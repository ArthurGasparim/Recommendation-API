# Destruição completa do ambiente AWS

## Objetivo

O `cleanup.sh` foi preparado para remover o ambiente temporário da iniciação e
interromper a cobrança dos recursos criados pelo projeto. A exclusão do cluster,
isoladamente, não é considerada suficiente: load balancers, volumes, imagens e
logs podem permanecer fora do ciclo de vida do EKS.

## Proteções contra perda acidental

- A execução normal exige digitar `DESTRUIR observability`.
- O PostgreSQL é exportado para `backups/` antes da primeira exclusão.
- Se o banco não estiver disponível, a execução para antes de destruir recursos.
- `--skip-backup` precisa ser informado explicitamente para aceitar a perda.
- O nome do cluster e a região são fixados por padrão em `observability` e
  `us-east-1`, mas podem ser substituídos por variáveis de ambiente.
- Nenhuma imagem Docker, backup ou configuração local é apagada.

## Ordem da remoção

1. Captura IDs de volumes, ALBs, Elastic IPs, VPC e provedor OIDC.
2. Cria o backup local do PostgreSQL.
3. Remove Ingresses e Services externos antes do controlador, permitindo que a
   AWS libere corretamente os load balancers.
4. Remove os manifests, Helm releases, namespaces e PVCs.
5. Remove AWS Load Balancer Controller, nós e control plane EKS.
6. Remove stacks CloudFormation residuais na ordem addon/nodegroup/cluster.
   Antes da stack principal, remove também o security group gerenciado pelo EKS
   que pode permanecer órfão e bloquear a exclusão da VPC. Durante a espera, o
   estado da stack é mostrado a cada 15 segundos.
7. Procura e remove EC2, ALB, target groups, EBS, snapshots, NAT, Elastic IPs,
   endpoints, interfaces e VPCs órfãs do projeto.
8. Remove os repositórios ECR e suas imagens, CloudWatch Log Groups, política IAM
   e provedor OIDC criados para o ambiente.
9. Executa novamente todas as consultas de auditoria.

O script retorna código diferente de zero se uma chamada falhar ou se a auditoria
final encontrar uma pendência. Dessa forma, uma saída parcial nunca é apresentada
como “custo zero”.

## Uso

Execução segura e interativa:

```bash
./cleanup.sh
```

Automação sem pergunta interativa, mantendo o backup:

```bash
./cleanup.sh --yes
```

Auditoria somente de leitura:

```bash
./cleanup.sh --audit-only
```

Destruição sem backup, somente quando a perda do banco for aceita:

```bash
./cleanup.sh --skip-backup
```

## Limite da garantia

A auditoria cobre os recursos criados pelo fluxo deste repositório e identificados
pelo nome, tags, stacks ou VPC do cluster. Ela não elimina cobranças históricas já
lançadas, impostos, serviços de outras regiões nem recursos alheios ao projeto.
Após uma auditoria limpa, o Cost Explorer ainda pode levar algum tempo para
refletir o encerramento porque os dados de faturamento não são instantâneos.
