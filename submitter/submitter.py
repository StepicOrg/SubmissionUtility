import argparse
import json
import requests
import sys
import time

client_id = "client_id"
client_secret = "client_secret"


auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
resp = requests.post('https://stepic.org/oauth2/token/', data={'grant_type': 'client_credentials'}, auth=auth)
token = (resp.json())['access_token']
stepic_url = "https://stepic.org/api"
headers = {'Authorization': 'Bearer ' + token, "content-type": "application/json"}


def exit_util(message):
    print(message, file=sys.stderr)
    sys.exit(0)


def get_lesson_id(url_parts):
    len_url_parts = len(url_parts)
    for i, part in enumerate(url_parts):
        if part == "lesson" and i + 1 < len_url_parts:
            return int(url_parts[i + 1].split("-")[-1])


def get_step_id(url_parts):
    len_url_parts = len(url_parts)
    for i, part in enumerate(url_parts):
        if part == "step" and i + 1 < len_url_parts:
            step_id = 0
            for x in url_parts[i + 1]:
                val = ord(x) - ord('0')
                if 0 <= val <= 9:
                    step_id = step_id * 10 + val
                else:
                    return step_id
    return 0


def set_problem(problem_url):
    tmp = requests.get(problem_url)
    code = tmp.status_code
    if code >= 500:
        exit_util("Can't connect to {}".format(problem_url))
    if code >= 400:
        exit_util("Oops some problems with your link {}".format(problem_url))
    print("\nSeting connecton to the page\n", file=sys.stderr)

    url_parts = problem_url.split("/")

    lesson_id = get_lesson_id(url_parts)
    step_id = get_step_id(url_parts)

    if lesson_id is None or not step_id:
        exit_util("Doesn't correct link.")

    url = stepic_url + "/lessons/{}".format(lesson_id)
    lesson_information = requests.get(url, headers=headers)
    lesson_information = lesson_information.json()
    try:
        step_id = lesson_information['lessons'][0]['steps'][step_id - 1]
        attempt = {"attempt": {
                               "step": str(step_id)
                            }
                   }
        url = stepic_url + "/attempts"
        attempt = requests.post(url, json.dumps(attempt), headers=headers)
        attempt = attempt.json()
        attempt_id = attempt['attempts'][0]['id']
        with open("attempt_id", "w") as file:
            file.write(str(attempt_id))
    except Exception as e:
        exit_util("Something went wrong =(")


def evaluate(attempt_id):
    print("Evaluating", file=sys.stderr)
    time_out = 0.1
    while True:
        url = stepic_url + "/submissions/{}".format(attempt_id)
        result = requests.get(url, headers=headers)
        result = result.json()
        status = result['submissions'][0]['status']
        if status != 'evaluation':
            break
        print("..", end="", flush=True, file=sys.stderr)
        time.sleep(time_out)
        time_out += time_out
    print(file=sys.stderr)
    print("You solution is {}".format(status), file=sys.stderr)


def submit_code(code):
    code = "".join(open(code).readlines())
    url = stepic_url + "/submissions"
    current_time = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    attemp_id = None
    with open("attempt_id") as file:
        attemp_id = file.readline()
    if attemp_id is None:
        exit_util("Plz, set the problem link!")
    submission = {"submission":
                    {
                        "time": current_time,
                        "reply":
                            {
                                "code": code,
                                "language": "c++11"
                            },
                        "attempt": attemp_id
                    }
    }
    submit = requests.post(url, json.dumps(submission), headers=headers)
    submit = submit.json()
    evaluate(submit['submissions'][0]['id'])


parser = argparse.ArgumentParser()
parser.add_argument("--problem", help="Set problems link", type=str)
parser.add_argument("--code", help="Send your code to stepic", type=str)

args = parser.parse_args()
if args.problem:
    set_problem(args.problem)
if args.code:
    submit_code(args.code)
