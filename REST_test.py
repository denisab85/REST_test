import requests
from xml.etree import ElementTree
import json


def _assert(name, condition, value):
    out = str(name) + ": "
    if condition:
        result = "Pass"
    else:
        result = "Fail"
    out += result
    out = out + " [" + str(value)
    print(out + "]")
    if result == "Fail":
        exit(1)


def start_project(appliance_ip, automation_zip, run_id=""):
    # upload and run new project as is
    uri = "http://" + appliance_ip + "/api/run"
    if len(run_id) != 0:
        uri = uri + "/" + run_id

    # octet-stream upload
    data = open(automation_zip, 'rb').read()
    response = requests.post(uri, data=data, headers={'Content-Type': 'application/octet-stream'})

    # multipart upload
    # files = {'file': open(automation_zip, 'rb')}
    # response = requests.post(uri, files=files)

    status_code = int(response.status_code)
    try:
        content = response.json()
    except ValueError or json.decoder.JSONDecodeError:
        content = "JSON format error"
    return status_code, content


def stop(appliance_ip, kind, id):
    uri = "http://" + str(appliance_ip) + "/api/" + str(kind) + "/" + str(id) + "/stop"
    response = requests.put(uri)
    status_code = int(response.status_code)
    try:
        content = response.json()
    except ValueError or json.decoder.JSONDecodeError:
        content = "JSON format error"
    return status_code, content


def get_status(appliance_ip, kind, id=""):
    """
    kind = Get status for port(s)
    Get list of all runIds with basic metadata
    """
    uri = "http://" + appliance_ip + "/api/" + kind
    if len(id):
        uri = uri + "/" + id
    response = requests.get(uri)
    status_code = int(response.status_code)
    try:
        content = response.json()
    except ValueError or json.decoder.JSONDecodeError:
        content = "JSON format error"
    return status_code, content


def check_ports(appliance_ip, port_nums, expected_status):
    status, content = get_status(appliance_ip, "port")
    _assert("Status", status == 200, status)
    if status == 200:
        _assert("Content", isinstance(content, dict), type(content))
        if isinstance(content, dict):
            for port_num in port_nums:
                result = False
                status = "not found"
                for port in content["ports"]:
                    status = port['status']
                    if port['port_id'] == port_num and status == expected_status:
                        result = True
                _assert(port_num, result, status)
            # singlePort = get_status(appliance_ip, "port", portNum)
            # _assert(ports[portNum].portid, (ports[portNum].status == singlePort.status), singlePort.status)


def get_app_info(appliance_ip):
    uri = "http://" + appliance_ip + "/app/getAppInfo2"
    response = requests.post(uri)
    status_code = int(response.status_code)
    tree = ElementTree.fromstring(response.content)
    ver = tree.findall("./portconfig/version")  # ./SwiftTest/portconfig/version
    return ver[0].text


# ======================================================================================= #


# test_ip = "172.17.1.54"
# test_ip = "192.168.8.104"
test_ip = "192.168.8.209"
# test_ip = "localhost:8104"
test_ports = 0, 1
project_file = "Automation.zip"
project_fileWithPortMismatch = "Automation-port-0-4.zip"
run_id = "test-project-0001"


ver = get_app_info(test_ip)
print("Backend version: " + ver)

print("\nStop all ports used in this project")
# stop all ports used in this project
for portNum in test_ports:
    status, content = stop(test_ip, "port", portNum)
    _assert("Status", status == 200, status)
    if status == 200:
        _assert("Content", isinstance(content, dict), type(content))
        if isinstance(content, dict):
            _assert(portNum, (content["portId"] == portNum and content["status"] == "idle"), content)

print("\nCheck that all ports used in this project are idle")
# check that all ports used in this project are idle 
check_ports(test_ip, test_ports, "idle")

print("\nPOST /api/run/{run_id} upload and run new project as is, with specified {run_id}")
status, content = start_project(test_ip, project_file, run_id)
_assert("Status", status == 200, status)
if status == 200:
    _assert("Content", isinstance(content, dict), type(content))
    if isinstance(content, dict):
        _assert("runId", content["runId"] == run_id, content["runId"])

print("\nCheck that all ports used in this project are busy")
# check that all ports used in this project are busy
check_ports(test_ip, test_ports, "busy")

print("\nCheck run status")
status, content = get_status(test_ip, "run", run_id)
_assert("Status", status == 200, status)
if status == 200:
    _assert("Content", isinstance(content, dict), type(content))
    if isinstance(content, dict):
        _assert("runId", content["runId"] == run_id, content)

print("\nGet list of all uploaded projects from appliance")
status, content = get_status(test_ip, "project")
_assert("Status", status == 200, status)
if status == 200:
    _assert("Content", isinstance(content, dict), type(content))
    if isinstance(content, dict):
        for project in content["projects"]:
            status, single_project = get_status(test_ip, "project", project["projectId"])
            _assert("Status", status == 200, status)
            if status == 200:
                _assert(project["projectId"], single_project == project, "Equal")

print("\nGet list of all runIds with basic metadata")
status, content = get_status(test_ip, "run")
if status == 200:
    _assert("Content", isinstance(content, dict), type(content))
    if isinstance(content, dict):
        print(content)
