import re
import requests
import json
from xml.etree import ElementTree


def get_app_info(appliance_ip):
    uri = "http://" + appliance_ip + "/app/getAppInfo2"
    response = requests.post(uri)
    status_code = int(response.status_code)
    tree = ElementTree.fromstring(response.content)
    ver = tree.findall("./portconfig/version")  # ./SwiftTest/portconfig/version
    return ver[0].text


# test_ip = "172.17.1.54"
# test_ip = "192.168.8.104"
# test_ip = "192.168.8.209"
# test_ip = "localhost:8104"
test_ip = "localhost:8209"

project_file = "./Data/Automation.zip"
project_fileWithPortMismatch = "Automation-port-0-4.zip"
run_id = "test-project-0001"


ver = get_app_info(test_ip)
print("Backend version: " + ver)

with open('Tests.json') as test_file:
    tests = json.load(test_file)

for test in tests:
    method = test["Method"]
    uri = test["URI"]
    uri_list = []
    content_type = 'text/plain'
    data = None
    files = None

    print('\n>>>>>>  ', test['Name'], '  <<<<<<')

    content = test.get('Content')
    if content:
        file_path = content['data']
        content_type = content['type']
        if content_type == 'application/octet-stream':
            data = open(file_path, 'rb').read()
        elif content_type == 'multipart/form-data':
            files = {'file': open(file_path, 'rb')}

    if not re.search("({\w+})", uri):
        uri_list.append(uri)

    for parameter in re.findall("({\w+})", uri):
        param_name = str(parameter[1:-1])
        param_value = test['Parameters'][param_name]
        if isinstance(param_value, list):
            for value in param_value:
                uri_list.append(uri.replace(parameter, str(value)))
        else:
            uri_list.append(uri.replace(parameter, param_value))

    for uri in uri_list:
        uri = "http://" + test_ip + uri
        print(method, uri)
        if method == "PUT":
            response = requests.put(uri, data=data, files=files, headers={'Content-Type': content_type})
        elif method == "GET":
            response = requests.get(uri, data=data, files=files, headers={'Content-Type': content_type})
        elif method == "POST":
            response = requests.post(uri, data=data, files=files, headers={'Content-Type': content_type})

        status_code = int(response.status_code)
        try:
            content = response.json()
        except ValueError or json.decoder.JSONDecodeError:
            content = "JSON format error"

        if status_code == 200:
            print(status_code, 'OK')
        elif status_code == 404:
            print(status_code, response.content)
        else:
            print(status_code, content['errors'])
