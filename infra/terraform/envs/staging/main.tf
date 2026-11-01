terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
  }
  # Bucket and lock table are passed at init: see infra/terraform/README.md.
  backend "s3" {
    key     = "qufin/staging/terraform.tfstate"
    region  = "eu-west-1"
    encrypt = true
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      project     = "qufin"
      environment = "staging"
      managed_by  = "terraform"
    }
  }
}

variable "region" {
  type    = string
  default = "eu-west-1"
}

# Modules to add as the backlog reaches them: network (VPC, private subnets), kms,
# database (Postgres 16 + TimescaleDB, P1-03), raw_zone (S3 with object lock, P1-05),
# secrets (P1-33), orchestration (Dagster on ECS Fargate, P1-07).
