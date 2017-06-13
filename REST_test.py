import requests
import json
from xml.etree import ElementTree
from collections import Counter


def get_app_info(appliance_ip):
    uri = "http://" + appliance_ip + "/app/getAppInfo2"
    response = requests.post(uri)
    tree = ElementTree.fromstring(response.content)
    ver = tree.findall("./portconfig/version")  # ./SwiftTest/portconfig/version
    return ver[0].text


def insert_params(obj, parameters):
    if isinstance(parameters, dict):
        for param_name, param_value in parameters.items():
            if isinstance(obj, str):
                obj = obj.replace("{" + param_name + "}", str(param_value))
            elif isinstance(obj, dict):
                for name, value in obj.items():
                    if isinstance(value, str):
                        obj[name] = obj[name].replace("{" + param_name + "}", str(param_value))
    return obj


def validate(content, expected, level=0):
    result = True
    if isinstance(content, dict) and isinstance(expected, dict):
        for name, value in expected.items():
            # if level:
            print("")
            print(("\t" * level) + name, end="")
            result = result and validate(content[name], value, level+1)
    elif isinstance(content, list):
        for n in range(len(expected)):
            # content = sorted(content)
            # expected = sorted(expected)
            if level:
                print("")
            print(("\t" * level) + "[{}]".format(n), end="")
            result = result and validate(content[n], expected[n], level+1)
    elif isinstance(content, str) or isinstance(content, int):
        expected = str(expected)
        content = str(content)
        result = (expected == content)
        print("='{}':\t{}".format(expected, result), end="")
    else:
        result = False
    return result


def run_action(method, uri, expected):
    result = False
    uri = "http://" + test_ip + uri
    response = ""
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
        print(status_code, 'OK', end="")
        result = validate(content, expected)
        print("")
    elif status_code == 404:
        print(status_code, response.content)
    else:
        print(status_code, content['errors'])
    return result

# test_ip = "172.17.1.54"
# test_ip = "192.168.8.104"
# test_ip = "192.168.8.209"
test_ip = "localhost:8104"
# test_ip = "localhost:8209"


project_fileWithPortMismatch = "Automation-port-0-4.zip"


ver = get_app_info(test_ip)
print("Backend version: " + ver)

with open('Tests.json') as test_file:
    tests = json.load(test_file)

stats = Counter()

for test in tests:
    method = test["Method"]
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

    parameters = test.get('Parameters')
    uri = insert_params(test["URI"], parameters)
    expected = insert_params(test["Expected"], parameters)

    result = run_action(method, uri, expected)
    stats[result] += 1

print("\n============ totals ============")
for cnt, num in stats.items():
    print("{}: {}".format(cnt, num))
