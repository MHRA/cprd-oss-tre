locals {
  environment_prefix            = var.tre_id
  execution_tizezone            = "Europe/London"
  data_move_requests_queue_name = "data-move-requests"
  fully_qualified_namespace     = "sb-${var.tre_id}.servicebus.windows.net"
  version                       = replace(replace(replace(data.local_file.data_move_processor_version.content, "__version__ = \"", ""), "\"", ""), "\n", "")
}
