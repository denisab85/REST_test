import requests
import json
from xml.etree import ElementTree
from collections import Counter
from time import sleep


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
            print("")
            print(("\t" * level) + name, end="")
            result = result and validate(content.get(name), value, level+1)
    elif isinstance(content, list) and isinstance(expected, list):
        for n in range(len(expected)):
            if level:
                print("")
            print(("\t" * level) + "[{}]".format(n), end="")
            result = result and validate(content[n], expected[n], level+1)
    elif isinstance(content, str) or isinstance(content, int):
        expected = str(expected)
        content = str(content)
        result = (expected == content)
        print("='{}':\t".format(content), end="")
        if result:
            print("Pass", end="", flush=True)
        else:
            print("Fail [expected: '{}']".format(expected), end="")
    else:
        result = False
    return result


def run_action(description, method, uri, parameters, expected):
    description = insert_params(description, parameters)
    print('\n\n[ ', description, ' ]')
    result = True

    # temporary solution. macros like 'wait_until' and 'sleep' should be described in a separate json file
    # and should use basic methods which follow after 'else' here
    if method == "sleep":
        sleep(int(parameters.get("time", 0)))
    elif method == "wait_until":
        n = 1
        while True:
            response = requests.get("http://localhost:8104/api/port/{}".format(parameters["portId"])).json()
            if response == parameters:
                print("\nPass")
                break
            if n%10 == 0:
                print("*", end="", flush=True)
            else:
                print(".", end="", flush=True)
            n += 1
            sleep(1)
    else:
        uri = insert_params(uri, parameters)
        expected = insert_params(expected, parameters)
        result = False
        uri = "http://" + test_ip + uri
        response = ""
        print(method, uri)
        if method == "PUT":
            response = requests.put(uri, data=data, files=files, headers={'Content-Type': content_type})
        elif method == "GET":
            response = requests.get(uri, data=data, files=files, headers={'Content-Type': content_type}, stream=True)
        elif method == "POST":
            response = requests.post(uri, data=data, files=files, headers={'Content-Type': content_type})
        elif method == "DELETE":
            response = requests.delete(uri, data=data, files=files, headers={'Content-Type': content_type})

        status_code = int(response.status_code)
        try:
            content = response.json()
        except ValueError or json.decoder.JSONDecodeError:
            content = "JSON format error"

        if status_code == 200 or status_code == 201:
            print(status_code, 'OK', end="")
            if response.headers.get("Content-Type") == "application/octet-stream":
                with open('results.tgz', 'wb') as out_file:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            out_file.write(chunk)
                            out_file.flush()
                # with open('results.tgz', 'wb') as out_file:
                #     shutil.copyfileobj(response.raw, out_file)
                del response
            else:
                result = validate(content, expected)
            print("")
        elif status_code == 400:
            print(status_code, content['errors'])
        else:
            print(status_code, response.content)
    return result


# ====================================================================================

# test_ip = "172.17.1.54"
# test_ip = "192.168.8.104"
# test_ip = "192.168.8.209"
# test_ip = "localhost:8104"
test_ip = "localhost:8209"

test_file_path = './Tests/runId.json'
# test_file_path = './Tests/projectId.json'
# test_file_path = './Tests/auto_assign_id.json'


project_fileWithPortMismatch = "Automation-port-0-4.zip"


ver = get_app_info(test_ip)
print("Backend version: " + ver)

with open(test_file_path) as test_file:
    tests = json.load(test_file)

stats = Counter()

for test in tests:
    content_type = 'text/plain'
    data = None
    files = None

    content = test.get('Content')
    if content:
        file_path = content['data']
        content_type = content['type']
        if content_type == 'application/octet-stream':
            data = open(file_path, 'rb').read()
        elif content_type == 'multipart/form-data':
            files = {'file': open(file_path, 'rb')}

    parameters = test.get('Parameters')
    if test.get("Enabled", 1):
        description = test.get("Description")
        method = test.get("Method")
        uri = test.get("URI")
        expected = test.get("Expected")

        result = run_action(description, method, uri, parameters, expected)
        stats[result] += 1

print("\n============ totals ============")
for cnt, num in stats.items():
    print("{}: {}".format(cnt, num))
