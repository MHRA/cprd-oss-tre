locals {
  tre_shared_service_tags = {
    tre_id                = var.tre_id
    tre_shared_service_id = var.tre_resource_id
  }
  letsencrypt_updater_file_path = "${path.module}/ohdsi-perm-updater.zip"
  letsencrypt_updater_md5       = filemd5(local.letsencrypt_updater_file_path)
}