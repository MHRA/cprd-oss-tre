import asyncio
import json
import logging
import base64
import uuid

from resources.helpers import get_installation_id
from shared.logging import shell_output_logger, redact_sensitive_text


def azure_login_command(config):
    if config["vmss_msi_id"]:
        command = f"az login --identity --client-id {config['vmss_msi_id']}"
    else:
        command = (
            f"az login --service-principal "
            f"--client-id {config['arm_client_id']} "
            f"--password {config['arm_client_secret']} "
            f"--tenant {config['arm_tenant_id']}"
        )
    return command


def azure_acr_login_command(config):
    return f"az acr login --name {config['registry_server'].replace('.azurecr.io','')}"


def _normalize_nullable_firewall_param(parameter_name, parameter_value):
    if parameter_name not in {"rule_collections", "network_rule_collections"}:
        return parameter_value

    if parameter_value is None:
        return None

    if isinstance(parameter_value, str):
        normalized = parameter_value.strip().lower()
        if normalized in {"", "null", "none"}:
            return None

    return parameter_value


def _decode_porter_value(parameter_value):
    if parameter_value is None:
        return None

    if isinstance(parameter_value, str):
        try:
            decoded = base64.b64decode(parameter_value).decode("utf-8")
            return json.loads(decoded)
        except Exception:
            return parameter_value

    return parameter_value


def _encode_porter_value(parameter_value):
    if parameter_value is None:
        val = json.dumps(None)
        val_bytes = val.encode("utf-8")
        val_base64_bytes = base64.b64encode(val_bytes)
        return val_base64_bytes.decode("ascii")

    if isinstance(parameter_value, (dict, list)):
        val = json.dumps(parameter_value)
        val_bytes = val.encode("utf-8")
        val_base64_bytes = base64.b64encode(val_bytes)
        return val_base64_bytes.decode("ascii")

    return str(parameter_value)


async def _get_porter_installation(config, logger, installation_id):
    command = (
        f"{azure_login_command(config)} >/dev/null && "
        f"{azure_acr_login_command(config)} >/dev/null && "
        f"porter installations show \"{installation_id}\" --output json"
    )

    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=config["porter_env"])

    stdout, stderr = await proc.communicate()
    logger.info("porter installations show exited with %s", proc.returncode)

    if proc.returncode != 0:
        if stderr:
            shell_output_logger(stderr.decode(), '[stderr]', logger, logging.WARN)
        raise RuntimeError(f"Failed to get installation '{installation_id}'")

    if not stdout:
        raise RuntimeError(f"No output returned for installation '{installation_id}'")

    return json.loads(stdout.decode())


async def build_porter_command(config, logger, msg_body, custom_action=False):
    porter_parameter_keys = await get_porter_parameter_keys(config, logger, msg_body)
    bundle_name = msg_body.get("name", "")
    installation_id = get_installation_id(msg_body)
    porter_env = dict(config["porter_env"])

    logger.info("Building porter command for bundle=%s action=%s", bundle_name, msg_body.get("action"))

    resolved_params = {}
    resolved_raw_params = {}

    if porter_parameter_keys is None:
        logger.warning("Unknown porter parameters - explain probably failed.")
    else:
        logger.info("Porter parameter keys discovered for %s: %s", bundle_name, porter_parameter_keys)

        for parameter_name in porter_parameter_keys:
            parameter_value = None
            parameter_source = None

            if parameter_name in msg_body.get("parameters", {}):
                parameter_value = msg_body["parameters"][parameter_name]
                parameter_source = "msg_body.parameters"
            elif parameter_name in config:
                parameter_value = config[parameter_name]
                parameter_source = "config"
            elif parameter_name in msg_body:
                parameter_value = msg_body[parameter_name]
                parameter_source = "msg_body"
            else:
                parameter_value = get_special_porter_param_value(config, parameter_name, msg_body)
                if parameter_value is not None:
                    parameter_source = "special"

            if bundle_name == "tre-shared-service-firewall":
                parameter_value = _normalize_nullable_firewall_param(parameter_name, parameter_value)

            if parameter_value is not None or (
                bundle_name == "tre-shared-service-firewall"
                and parameter_name in {"rule_collections", "network_rule_collections"}
            ):
                encoded_value = _encode_porter_value(parameter_value)
                resolved_params[parameter_name] = encoded_value
                resolved_raw_params[parameter_name] = parameter_value
                logger.info(
                    "Mapped porter parameter '%s' from source '%s' type '%s' (length=%s)",
                    parameter_name,
                    parameter_source,
                    type(parameter_value).__name__,
                    len(encoded_value)
                )
            else:
                logger.info("No value resolved for porter parameter '%s'", parameter_name)

    # Special-case firewall:
    # - clean stale installation parameter overrides
    # - use installation apply instead of upgrade
    # - write literal parameter values into installation.parameters
    # - keep command line short by applying a JSON file from disk
    if bundle_name == "tre-shared-service-firewall":
        installation = await _get_porter_installation(config, logger, installation_id)

        installation_parameters = {}

        large_encoded_params = {"rule_collections", "network_rule_collections"}

        for parameter_name in porter_parameter_keys or []:
            if parameter_name in large_encoded_params and parameter_name in resolved_params:
                installation_parameters[parameter_name] = resolved_params[parameter_name]
                logger.info(
                    "Firewall installation parameter '%s' set with encoded string length=%s",
                    parameter_name,
                    len(resolved_params[parameter_name])
                )
            elif parameter_name in resolved_raw_params:
                installation_parameters[parameter_name] = resolved_raw_params[parameter_name]
                logger.info(
                    "Firewall installation parameter '%s' set with literal type '%s'",
                    parameter_name,
                    type(resolved_raw_params[parameter_name]).__name__
                )

        installation["parameters"] = installation_parameters

        logger.info(
            "Rebuilt firewall installation parameters with names: %s",
            list(installation_parameters.keys())
        )

        inst_file = f"/tmp/{installation_id}-installation.json"
        with open(inst_file, "w", encoding="utf-8") as f:
            json.dump(installation, f)

        logger.info("Firewall installation apply file path: %s", inst_file)

        command = (
            f"{azure_login_command(config)} && "
            f"{azure_acr_login_command(config)} && "
            f"porter installation apply {inst_file}"
        )

        command_line = [command]
        logger.info("command_line %s", redact_sensitive_text(str(command_line)))
        return command_line, inst_file, porter_env

    # Default path for non-firewall bundles only
    param_set_entries = []
    param_set_file = None

    for parameter_name, parameter_value in resolved_params.items():
        env_name = f"TRE_PARAM_{parameter_name.upper()}"
        porter_env[env_name] = parameter_value
        param_set_entries.append({
            "name": parameter_name,
            "source": {"env": env_name}
        })

    command = f"{azure_login_command(config)} && {azure_acr_login_command(config)} &&"

    if param_set_entries:
        param_set_name = f"tre-params-{installation_id}-{uuid.uuid4().hex[:8]}"
        param_set_file = f"/tmp/{param_set_name}.json"
        param_set = {
            "schemaType": "ParameterSet",
            "schemaVersion": "1.0.1",
            "name": param_set_name,
            "namespace": "",
            "parameters": param_set_entries
        }

        with open(param_set_file, "w", encoding="utf-8") as f:
            json.dump(param_set, f)

        command += f" porter parameters apply {param_set_file} &&"

    command += (
        f" porter{' invoke --action' if custom_action else ''}"
        f" {msg_body['action']} \"{installation_id}\""
        f" --reference {config['registry_server']}/{msg_body['name']}:v{msg_body['version']}"
    )

    if param_set_entries:
        command += f" --parameter-set {param_set['name']}"

    command += (
        f" --force"
        f" --credential-set arm_auth"
        f" --credential-set aad_auth"
    )

    command_line = [command]
    logger.info("command_line %s", redact_sensitive_text(str(command_line)))
    return command_line, param_set_file, porter_env


async def build_porter_command_for_outputs(msg_body):
    installation_id = get_installation_id(msg_body)
    command_line = [f"porter installations output list --installation {installation_id} --output json"]
    return command_line


async def get_porter_parameter_keys(config, logger, msg_body):
    command = [f"{azure_login_command(config)} >/dev/null && \
        {azure_acr_login_command(config)} >/dev/null && \
        porter explain --reference {config['registry_server']}/{msg_body['name']}:v{msg_body['version']} --output json"]

    proc = await asyncio.create_subprocess_shell(
        ''.join(command),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=config["porter_env"])

    stdout, stderr = await proc.communicate()
    logging.info("get_porter_parameter_keys exited with %s", proc.returncode)

    if stdout:
        result_stdout = stdout.decode()
        porter_explain_parameters = json.loads(result_stdout)["parameters"]
        porter_parameter_keys = [item["name"] for item in porter_explain_parameters]
        return porter_parameter_keys

    if stderr:
        result_stderr = stderr.decode()
        shell_output_logger(result_stderr, '[stderr]', logger, logging.WARN)

    return None


def get_special_porter_param_value(config, parameter_name: str, msg_body):
    if parameter_name == "mgmt_acr_name":
        return config["registry_server"].replace('.azurecr.io', '')
    if parameter_name == "mgmt_resource_group_name":
        return config["tfstate_resource_group_name"]
    if parameter_name == "workspace_id":
        return msg_body.get("workspaceId")
    if parameter_name == "parent_service_id":
        return msg_body.get("parentWorkspaceServiceId")
    if (value := config["bundle_params"].get(parameter_name.lower())) is not None:
        return value

    return None
