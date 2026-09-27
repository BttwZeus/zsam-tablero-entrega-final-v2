terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

# --- S3: adjuntos de las tarjetas ---
# Privado, con bloqueo total de acceso publico y cifrado en reposo (SSE-S3).

resource "aws_s3_bucket" "adjuntos" {
  bucket = "${var.app_name}-adjuntos-${data.aws_caller_identity.current.account_id}"
  # Se fija explicitamente en false: algunas cuentas de AWS Academy tienen una
  # politica de organizacion (SCP) que bloquea la llamada de lectura de Object
  # Lock que Terraform hace por defecto. Fijarlo evita esa llamada.
  object_lock_enabled = false
}

resource "aws_s3_bucket_public_access_block" "adjuntos" {
  bucket = aws_s3_bucket.adjuntos.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "adjuntos" {
  bucket = aws_s3_bucket.adjuntos.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# --- RDS: base de datos de la aplicacion ---
# Cifrada, sin acceso publico, solo alcanzable desde el security group de la app.

resource "aws_security_group" "rds" {
  name        = "${var.app_name}-rds-sg"
  description = "Permite Postgres solo desde la instancia de la aplicacion"

  ingress {
    description = "Postgres desde la app"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.allowed_app_cidr]
  }

  # Sin regla de egress: la RDS solo responde conexiones entrantes en 5432,
  # no necesita iniciar trafico saliente.
}

resource "aws_db_instance" "tablero" {
  identifier     = "${var.app_name}-db"
  engine         = "postgres"
  engine_version = "16.9"
  instance_class = "db.t3.micro"

  allocated_storage     = 20
  storage_encrypted     = true
  db_name                = var.db_name
  username                = var.db_username
  password                = var.db_password

  publicly_accessible    = false
  vpc_security_group_ids = [aws_security_group.rds.id]
  skip_final_snapshot    = true
  deletion_protection    = false

  backup_retention_period    = 1
  auto_minor_version_upgrade = true
  copy_tags_to_snapshot      = true
  enabled_cloudwatch_logs_exports = ["postgresql"]
}
