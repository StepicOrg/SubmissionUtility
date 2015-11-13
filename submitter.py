import click
import json
import requests
import os
import sys
import time

client_id = "client_id"
client_secret = "client_secret"
stepic_url = "https://stepic.org/api"
client_file = os.environ['HOME'] + "/.submitter/client_file"
token = None
headers = None


def exit_util(message):
    print(message, file=sys.stderr)
    sys.exit(0)


def update_client():
    global client_id
    global client_secret
    global token
    global headers
    with open(client_file, "r") as f:
        client_id = f.readline()
        client_id = client_id.split(":")[-1].rstrip()
        client_secret = f.readline()
        client_secret = client_secret.split(":")[-1].rstrip()  
    auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
    resp = requests.post('https://stepic.org/oauth2/token/', data={'grant_type': 'client_credentials'}, auth=auth)
    if resp.status_code > 400:
        exit_util("Lost connection")    
    token = (resp.json())['access_token']
    headers = {'Authorization': 'Bearer ' + token, "content-type": "application/json"}


programming_language = {'cpp': 'c++11', 'c': 'c++11', 'py': 'python3',
                        'java': 'java8', 'hs': 'haskel 7.10', 'sh': 'shell',
                        'r': 'r'}
                        
                        
def set_client(cid, secret):
    with open(client_file, "r") as f:
        lines = [line.split(":")[-1].rstrip() for line in f]
    with open(client_file, "w") as f:
        f.writelines("client_id:{}\n".format(cid or lines[0]))
        f.writelines("client_secret:{}\n".format(secret or lines[1]))

        
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
    update_client()
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
    update_client()
    file_name = code
    code = "".join(open(code).readlines())
    url = stepic_url + "/submissions"
    current_time = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    attempt_id = None
    with open("attempt_id") as file:
        attempt_id = file.readline()
    if attempt_id is None:
        exit_util("Plz, set the problem link!")
    language = programming_language.get(file_name.split('.')[-1])
    if language is None:
        exit_util("Doesn't correct extension for programme.")
    submission = {"submission":
                    {
                        "time": current_time,
                        "reply":
                            {
                                "code": code,
                                "language": language
                            },
                        "attempt": attempt_id
                    }
    }
    submit = requests.post(url, json.dumps(submission), headers=headers)
    submit = submit.json()
    evaluate(submit['submissions'][0]['id'])


@click.group()
@click.version_option()
def main():
    """Submitter 1.0
       
       Tools for submitting solutions to stepic.org
    """
    try:
        os.mkdir(os.environ['HOME'] + "/.submitter")
    except Exception:
        pass
    print("HERE")
    lines = 0
    try:
        with open(client_file, "r") as f:
            for _ in f:
                lines += 1
    except Exception as e:
        pass
    if lines < 2:
        with open(client_file, "w") as f:
            f.writelines("client_id:\n")
            f.writelines("client_secret:\n")    



@main.command()
@click.option("--link", help="Link to your problem")
def remember_problem(link=None):
    """     Rember and Set the current problem.

    """
    if not link is None:
        set_problem(link)


@main.command()
@click.option("--solution", help="Path to your solution")
def submit_action(solution=None):
    """ Submit a solution.

    """
    if not solution is None:
        submit_code(solution)

@main.command()
@click.option("--cid", help="Your client-id. If you don't have it, please create on https://stepic.org/oauth2/applications/")
def set_client_id(cid=None):
    if not cid is None:
        set_client(cid, None)
    click.echo("Client id has been changed!")
        

@main.command()
@click.option("--csecret", help="Your client-secret. If you don't vae it, please create on https://stepic.org/oauth2/applications/")
@click.pass_context
def set_secret(ctx, csecret):
    if not csecret is None:
        set_client(None, csecret)    
    click.echo("Client secret has been changed!")

