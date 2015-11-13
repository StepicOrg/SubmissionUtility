import click
import json
import requests
import os
import sys
import time

client_id = "client_id"
client_secret = "client_secret"
stepic_url = "https://stepic.org/api"
client_file = ".submitter/client_file"
attempt_file = ".submitter/attempt_file"
token = None
headers = None
file_manager = None


class FileManager:
    """Local file manager"""

    def __init__(self):
        self.home = os.path.expanduser("~")
        self.divide_symbol = "/"
        from platform import system
        if system() == "Windows":
            self.divide_symbol = "\\"

    def create_dir(self, dir_name):
        dir_name = self.get_name(dir_name)
        try:
            os.mkdir(dir_name)
        except FileExistsError as e:
            return

    def get_name(self, filename):
        return self.home + self.divide_symbol + filename

    def read_file(self, filename):
        filename = self.get_name(filename)
        with open(filename, "r") as file:
            for line in file:
                yield line

    def write_to_file(self, filename, content):
        filename = self.get_name(filename)
        with open(filename, "w") as file:
            file.writelines(content)


def exit_util(message):
    click.echo(message)
    sys.exit(0)


def update_client():
    global client_id
    global client_secret
    global token
    global headers
    f = file_manager.read_file(client_file)
    client_id = next(f)
    client_id = client_id.split(":")[-1].rstrip()
    client_secret = next(f)
    client_secret = client_secret.split(":")[-1].rstrip()
    auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
    resp = requests.post('https://stepic.org/oauth2/token/', data={'grant_type': 'client_credentials'}, auth=auth)
    if resp.status_code > 400:
        exit_util("Wrong Client id or Client secret.\n Or check your internet connection.")
    token = (resp.json())['access_token']
    headers = {'Authorization': 'Bearer ' + token, "content-type": "application/json"}


programming_language = {'cpp': 'c++11', 'c': 'c++11', 'py': 'python3',
                        'java': 'java8', 'hs': 'haskel 7.10', 'sh': 'shell',
                        'r': 'r'}
                        
                        
def set_client(cid, secret):
    lines = [line.split(":")[-1].rstrip() for line in file_manager.read_file(client_file)]
    to_write = "client_id:{}\nclient_secret:{}\n".format(cid or lines[0], secret or lines[1])
    file_manager.write_to_file(client_file, to_write)

        
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
        file_manager.write_to_file(attempt_file, str(attempt_id))
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
    file = file_manager.read_file(attempt_file)
    attempt_id = next(file)
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
    global file_manager
    file_manager = FileManager()
    try:
        file_manager.create_dir(".submitter")
    except Exception:
        click.echo("Can't do anything. Not enough rights to edit folders.")
        exit(0)
    lines = 0
    for _ in file_manager.read_file(client_file):
        lines += 1
    if lines < 2:
        file_manager.write_to_file(client_file, "client_id:\nclient_secret:\n")


@main.command()
def init():
    click.echo("Before using, create new Application on https://stepic.org/oauth2/applications/")
    try:
        click.echo("Enter your Client id:")
        new_client_id = input()
        click.echo("Enter your Client secret:")
        new_client_secret = input()
        set_client(new_client_id, new_client_secret)
        update_client()
    except Exception:
        exit_util("Enter right Client id and Client secret")


@main.command()
@click.option("--p", help="Link to your problem")
def problem(p=None):
    """     Rember and Set the current problem.

    """
    if not (p is None):
        set_problem(p)


@main.command()
@click.option("--s", help="Path to your solution")
def submit(s=None):
    """ Submit a solution.

    """
    if not (s is None):
        submit_code(s)


@main.command()
@click.option("--cid", help="Your client-id. If you don't have it," +
                            "please create on https://stepic.org/oauth2/applications/")
def client(cid=None):
    if not (cid is None):
        set_client(cid, None)
    click.echo("Client id has been changed!")
        

@main.command()
@click.option("--cs", help="Your client-secret. If you don't vae it," +
                           " please create on https://stepic.org/oauth2/applications/")
@click.pass_context
def secret(ctx, cs):
    if not (cs is None):
        set_client(None, cs)
    click.echo("Client secret has been changed!")

