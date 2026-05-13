locals {
  environment_prefix            = var.tre_id
  execution_tizezone            = "Europe/London"
  data_move_requests_queue_name = "data-move-requests"
  version                       = replace(replace(replace(data.local_file.data_move_processor_version.content, "__version__ = \"", ""), "\"", ""), "\n", "")
}
