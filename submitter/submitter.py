import argparse
import json
import requests
import sys
import time

client_id = "gGgXy4iks8VFjks691bcaCPBAizvpabUSioLrlJY"
client_secret = "nZvZshi9cas8sNld86Nk5ZbAHTkWwZ8OErsdfh2UA77pZ2DfeXtSklbCLtMDGop7Q6pWXCE7cEzTb9YBCoqJVqd7XiiNqPpbf3RUSlqmaols0IdvwlWSiiHtBTYozc9m"

auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
resp = requests.post('https://stepic.org/oauth2/token/', data={'grant_type': 'client_credentials'}, auth=auth)
token = json.loads(resp.text)['access_token']
stepic_url = "https://stepic.org/api"
headers = {'Authorization': 'Bearer ' + token, "content-type": "application/json"}


def set_problem(problem_url):
    tmp = requests.get(problem_url)
    code = tmp.status_code
    if code >= 500:
        raise Exception("Can't connect to {}".format(problem_url))
    if code >= 400:
        raise Exception("Oops some problems with your link {}"/format(problem_url))
    sys.stderr.write("Seting connecton to the page\n")
    tmp = None
    try:
        tmp = problem_url.split("/")
        tmp = tmp[-1]
    except Exception as e:
        raise Exception("Doesn't a correct stepic address.") from e
    unit = None
    position = None
    try:
        [position, unit] = tmp.split("?unit=")
        position = int(position) - 1
        assert position >= 0
    except Exception as e:
        raise Exception("Last slash doesn't math %d?unit=%d patern") from e
    url = stepic_url + "/units/{}".format(unit)
    get_units = requests.get(url, headers=headers)
    get_units = json.loads(get_units.text)
    assignment = None
    try:
        assignment = get_units['units'][0]['assignments'][position]
    except Exception as e:
        raise Exception("Check your link")
    try:
        url = stepic_url + "/assignments/{}".format(assignment)
        get_assignment = requests.get(url, headers=headers)
        get_assignment = json.loads(get_assignment.text)
        step_id = get_assignment['assignments'][0]['step']
        attempt = {"attempt": {
                               "time": None,
                               "dataset_url": None,
                               "status": None,
                               "time_left": None,
                               "step": str(step_id),
                               "user": None
                            }
                   }
        url = stepic_url + "/attempts"
        attempt = requests.post(url, json.dumps(attempt), headers=headers)
        attempt = json.loads(attempt.text)
        attempt_id = attempt['attempts'][0]['id']
        with open("attempt_id", "w") as file:
            file.write(str(attempt_id))
    except Exception as e:
        pass


def evaluate(attempt_id):
    print("Evaluating\n", end="")
    while True:
        url = stepic_url + "/submissions/{}".format(attempt_id)
        result = requests.get(url, headers=headers)
        result = json.loads(result.text)
        status = result['submissions'][0]['status']
        if status != 'evaluation':
            break
        print("..", end="", flush=True)
    print()
    print("You solution is {}".format(status))


def submit_code(code):
    code = "".join(open(code).readlines())
    url = stepic_url + "/submissions"
    current_time = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    attemp_id = None
    with open("attempt_id") as file:
        attemp_id = file.readline()
    if attemp_id is None:
        raise Exception("Plz, set the problim link!")
    submission = {"submission":
                    {
                        "status": None,
                        "score": None,
                        "hint": None,
                        "time": current_time,
                        "reply":
                            {
                                "code": code,
                                "language": "c++11"
                            },
                        "reply_url": None,
                        "attempt_id": None,
                        "has_attempt": False,
                        "session_id": None,
                        "has_session": False,
                        "attempt": attemp_id,
                        "session": None
                    }
    }
    submit = requests.post(url, json.dumps(submission), headers=headers)
    submit = json.loads(submit.text)
    evaluate(submit['submissions'][0]['id'])


parser = argparse.ArgumentParser()
parser.add_argument("--problem", help="Set problems link", type=str)
parser.add_argument("--code", help="Send your code to stepic", type=str)

args = parser.parse_args()
if args.problem:
    set_problem(args.problem)
if args.code:
    submit_code(args.code)
