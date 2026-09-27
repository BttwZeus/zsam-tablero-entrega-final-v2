output "s3_bucket_name" {
  value = aws_s3_bucket.adjuntos.bucket
}

output "rds_endpoint" {
  value = aws_db_instance.tablero.address
}
