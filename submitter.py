#!/usr/bin/env python
import click
import json
import os
import re
import requests
import sys
import time

STEPIC_URL = "https://stepic.org/api"
APP_FOLDER = ".stepic"
CLIENT_FILE = APP_FOLDER + "/client_file"
ATTEMPT_FILE = APP_FOLDER + "/attempt_file"
token = None
headers = None
file_manager = None
client = None


class Client:
    def __init__(self):
        self.id = "client_id"
        self.secret = "secret"

    def set_id(self, client_id):
        self.id = client_id

    def set_secret(self, client_secret):
        self.secret = client_secret

    def get_id(self):
        return self.id

    def get_secret(self):
        return self.secret


class FileManager:
    """Local file manager"""

    def __init__(self):
        self.home = os.path.expanduser("~")

    def create_dir(self, dir_name):
        dir_name = self.get_name(dir_name)
        try:
            os.mkdir(dir_name)
        except FileExistsError as e:
            return

    def get_name(self, filename):
        return os.path.join(self.home, filename)

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
    click.secho(message, fg="red")
    sys.exit(0)


def update_client():
    global token
    global headers
    global client
    f = file_manager.read_file(CLIENT_FILE)
    client_id = next(f)
    client_id = client_id.split(":")[-1].rstrip()
    client.set_id(client_id)
    client_secret = next(f)
    client_secret = client_secret.split(":")[-1].rstrip()
    client.set_secret(client_secret)
    auth = requests.auth.HTTPBasicAuth(client.get_id(), client.get_secret())
    resp = requests.post('https://stepic.org/oauth2/token/', data={'grant_type': 'client_credentials'}, auth=auth)
    if resp.status_code > 400:
        exit_util("Wrong Client id or Client secret.\n Or check your internet connection.")
    token = (resp.json())['access_token']
    headers = {'Authorization': 'Bearer ' + token, "content-type": "application/json"}


programming_language = {'cpp': 'c++11', 'c': 'c++11', 'py': 'python3',
                        'java': 'java8', 'hs': 'haskel 7.10', 'sh': 'shell',
                        'r': 'r'}
                        
                        
def set_client(cid, secret):
    lines = [line.split(":")[-1].rstrip() for line in file_manager.read_file(CLIENT_FILE)]
    to_write = "client_id:{}\nclient_secret:{}\n".format(cid or lines[0], secret or lines[1])
    file_manager.write_to_file(CLIENT_FILE, to_write)

        
def get_lesson_id(problem_url):
    match = re.search(r'lesson/.*?(\d+)/', problem_url)
    if match is None:
        return match
    return match.group(1)


def get_step_id(problem_url):
    match = re.search(r'step/(\d+)', problem_url)
    if match is None:
        return 0
    return int(match.group(1))


def set_problem(problem_url):
    update_client()
    request_inf = None
    try:
        request_inf = requests.get(problem_url)
    except Exception as e:
        exit_util("The link is incorrect.")
    code = request_inf.status_code
    if code >= 500:
        exit_util("Can't connect to {}".format(problem_url))
    if code >= 400:
        exit_util("Oops some problems with your link {}".format(problem_url))
    click.secho("\nSetting connection to the page..", bold=True)

    lesson_id = get_lesson_id(problem_url)
    step_id = get_step_id(problem_url)

    if lesson_id is None or not step_id:
        exit_util("The link is incorrect.")

    url = STEPIC_URL + "/lessons/{}".format(lesson_id)
    lesson_information = requests.get(url, headers=headers)
    lesson_information = lesson_information.json()
    try:
        step_id = lesson_information['lessons'][0]['steps'][step_id - 1]
        attempt = {"attempt": {
                               "step": str(step_id)
                            }
                   }
        url = STEPIC_URL + "/attempts"
        attempt = requests.post(url, json.dumps(attempt), headers=headers)
        attempt = attempt.json()
        attempt_id = attempt['attempts'][0]['id']
        file_manager.write_to_file(ATTEMPT_FILE, str(attempt_id))
    except Exception as e:
        exit_util("You do not have permission to perform this action, or something went wrong.")
    click.secho("Connecting completed!", fg="green")


def evaluate(attempt_id):
    click.secho("Evaluating", bold=True, fg='white')
    time_out = 0.1
    while True:
        url = STEPIC_URL + "/submissions/{}".format(attempt_id)
        result = requests.get(url, headers=headers)
        result = result.json()
        status = result['submissions'][0]['status']
        if status != 'evaluation':
            break
        click.echo("..", nl=False)
        time.sleep(time_out)
        time_out += time_out
    click.echo("")
    click.secho("You solution is {}".format(status), fg=['red', 'green'][status == 'correct'])


def submit_code(code):
    update_client()
    file_name = code
    code = "".join(open(code).readlines())
    url = STEPIC_URL + "/submissions"
    current_time = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    file = file_manager.read_file(ATTEMPT_FILE)
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
    """
    Submitter 0.2
    Tools for submitting solutions to stepic.org
    """
    global file_manager
    global client
    file_manager = FileManager()
    client = Client()
    try:
        file_manager.create_dir(APP_FOLDER)
    except OSError:
        exit_util("Can't do anything. Not enough rights to edit folders.")
    lines = 0
    try:
        for _ in file_manager.read_file(CLIENT_FILE):
            lines += 1
    except Exception:
        pass
    if lines < 2:
        file_manager.write_to_file(CLIENT_FILE, "client_id:\nclient_secret:\n")


@main.command()
def init():
    """
    Initializes utility: entering client_id and client_secret
    """
    click.echo("Before using, create new Application on https://stepic.org/oauth2/applications/")
    click.secho("Client type - Confidential, Authorization grant type - Client credentials.", fg="red", bold=True)

    try:
        click.secho("Enter your Client id:", bold=True)
        new_client_id = input()
        click.secho("Enter your Client secret:", bold=True)
        new_client_secret = input()
        set_client(new_client_id, new_client_secret)
        update_client()
    except Exception:
        exit_util("Enter right Client id and Client secret")
    click.secho("Submitter was inited successfully!", fg="green")


@main.command()
@click.option("-p", help="Link to your problem")
def problem(p=None):
    """
    Setting new problem as current target.
    """
    if p is not None:
        set_problem(p)


@main.command()
@click.option("-s", help="Path to your solution")
def submit(s=None):
    """
    Submit a solution to stepic system.
    """
    if s is not None:
        submit_code(s)

if __name__ == '__main__':
    main()