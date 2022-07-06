import json
from typing import Optional

import requests
import urllib3

urllib3.disable_warnings()


STATE_OK = 0
STATE_WARNING = 1
STATE_CRITICAL = 2
STATE_UNKNOWN = 3

States = {
    STATE_OK: 'OK',
    STATE_WARNING: 'WARNING',
    STATE_CRITICAL: 'CRITICAL',
    STATE_UNKNOWN: 'UNKNOWN',
}


def send_passive_check(url: str, user: str, password: str, status: int,
                       host_name: str, service_name: str,
                       text_output: str,
                       performance_data: Optional[str] = None):
    """
    https://icinga.com/docs/icinga-2/latest/doc/12-icinga2-api/#process-check-result

    [icinga]
    url
    user
    password
    """
    request_url = '{}/v1/actions/process-check-result'.format(url)
    headers = {
        'Accept': 'application/json',
        'X-HTTP-Method-Override': 'POST'
    }
    data = {
        'type': 'Service',
        'filter': 'host.name=="{}" && service.name=="{}"'.format(host_name,
                                                                 service_name),
        'exit_status': status,
        'plugin_output': text_output,
    }

    if performance_data:
        data['performance_data'] = performance_data

    return requests.post(request_url,
                         headers=headers,
                         auth=(user, password),
                         data=json.dumps(data), verify=False)
