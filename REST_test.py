import requests
import json
from xml.etree import ElementTree
from collections import Counter
from time import sleep
import copy


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


def run_action(test_ip, action, parameters):
    description = insert_params(action["Description"], parameters)
    method = action["Method"]
    print('\n\n[ ', description, ' ]')
    result = True
    output = dict()
    data = None
    files = None

    for par in action.get("Parameters"):
        if par not in parameters:
            print("Parameter not found:", par)
            return False

    if method in ("GET", "PUT", "POST", "DELETE"):
        uri = action["URI"]
        uri = insert_params(uri, parameters)
        content_type = parameters.get("content-type", "text/plain")

        result = False
        uri = "http://" + test_ip + uri
        response = ""
        print(method, uri)
        if method == "PUT":
            response = requests.put(uri, data=data, files=files, headers={'Content-Type': content_type})
        elif method == "GET":
            response = requests.get(uri, data=data, files=files, headers={'Content-Type': content_type}, stream=True)
        elif method == "POST":
            file_path = parameters.get("data", None)
            if file_path:
                if content_type == 'application/octet-stream':
                    data = open(file_path, 'rb').read()
                elif content_type == 'multipart/form-data':
                    files = {'file': open(file_path, 'rb')}
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
                del response
            else:
                if "Validate" in action:
                    expected = copy.deepcopy(action["Validate"])
                    expected = insert_params(expected, parameters)
                    result = validate(content, expected)
            print("")
            if "Output" in action:
                for item in action["Output"]:
                    output[item] = content.get(item)
        elif status_code == 400:
            print(status_code, content['errors'])
        else:
            print(status_code, response.content)
    elif method == "sleep":
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
    return result, output


# ====================================================================================

# test_ip = "172.17.1.54"
# test_ip = "192.168.8.104"
test_ip = "192.168.8.209"
# test_ip = "localhost:8104"
# test_ip = "localhost:8209"

# project_path = './Tests/runId.json'
project_path = './Tests/projectId.json'
# project_path = './Tests/auto_assign_id.json'

with open("./actions.json") as actions_file:
    actions = json.load(actions_file)

# ver = get_app_info(test_ip)
# print("Backend version: " + ver)

with open(project_path) as test_file:
    project = json.load(test_file)

stats = Counter()

for action in project:
    if action.get("Enabled", 1):
        action_name = action.get("Action")
        if len(action_name):
            if action_name in actions:
                parameters = action.get("Parameters", None)
                if parameters:
                    result, output = run_action(test_ip, actions[action_name], parameters)
                    if action.get("Validate"):
                         result = result and validate(action["Validate"], output)
                         stats[result] += 1
                else:
                    print("No parameters found for action: " + action_name)
            else:
                 print("Action not found: '{}'".format(action.get("Action")))
        else:
            print("Action name can not be empty")

print("\n============ totals ============")
for cnt, num in stats.items():
    print("{}: {}".format(cnt, num))
