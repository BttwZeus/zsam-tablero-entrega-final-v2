variable "aws_region" {
  description = "Region de AWS donde se crean los recursos"
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "Nombre corto del proyecto, usado como prefijo de recursos"
  type        = string
  default     = "gestor-tareas"
}

variable "db_name" {
  description = "Nombre de la base de datos"
  type        = string
  default     = "tablero"
}

variable "db_username" {
  description = "Usuario administrador de la base de datos"
  type        = string
  default     = "tablero"
}

variable "db_password" {
  description = "Password del usuario administrador de la base de datos (no tiene default a proposito: se pasa por TF_VAR_db_password o -var, nunca se comitea)"
  type        = string
  sensitive   = true
}

variable "allowed_app_cidr" {
  description = "CIDR desde el que la instancia de la aplicacion puede alcanzar la RDS (la IP/subred de tu instancia EC2 del Learner Lab)"
  type        = string
}
