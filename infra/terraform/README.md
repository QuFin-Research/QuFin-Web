# Infrastructure (Terraform)

Skeleton for the AWS foundation in the Blueprint (section 06) and backlog task P0-10. **Not
applied yet**: it needs the AWS Organization (P0-09) and the state bucket to exist first.

```
envs/dev      one root module per account (dev, staging, prod)
envs/staging
envs/prod
```

Each environment will hold: remote state in S3 with a DynamoDB lock, a VPC with private subnets,
KMS keys, the Postgres 16 + TimescaleDB instance (P1-03), the S3 raw zone with versioning and
object lock (P1-05), Secrets Manager entries for source API keys (P1-33) and Dagster on ECS
Fargate (P1-07).

To start, after the accounts exist:

```bash
cd infra/terraform/envs/dev
terraform init -backend-config="bucket=<state-bucket>" -backend-config="dynamodb_table=<lock-table>"
terraform plan
```

Never commit `*.tfvars` with secrets or account IDs; they are ignored by git.
