

# https://icinga.com/docs/icinga-2/latest/doc/12-icinga2-api/#process-check-result

import requests
import json
from typing import Optional
import urllib3
urllib3.disable_warnings()

# [icinga]
# url
# user
# password


def send_passive_check(url: str, user: str, password: str, host_name: str,
                       service_name: str, exit_status: int,
                       plugin_output: str,
                       performance_data: Optional[str] = None):
    request_url = '{}/v1/actions/process-check-result'.format(url)
    headers = {
        'Accept': 'application/json',
        'X-HTTP-Method-Override': 'POST'
    }
    data = {
        'type': 'Service',
        'filter': 'host.name=="{}" && service.name=="{}"'.format(host_name,
                                                                 service_name),
        'exit_status': exit_status,
        'plugin_output': plugin_output,
    }

    if performance_data:
        data['performance_data'] = performance_data

    return requests.post(request_url,
                         headers=headers,
                         auth=(user, password),
                         data=json.dumps(data), verify=False)


# result = send_passive_check(host_name='xps', service_name='apt',
#                               exit_status=0, plugin_output='API test')

# print(result.status_code)
# print(result.text)
# result.raise_for_status()
