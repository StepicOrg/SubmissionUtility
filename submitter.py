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
file_manager = None
stepic_client = None


class StepicClient:
    """Client to communicate with api"""

    def __init__(self, file_manager):
        self.file_manager = file_manager
        data = self.file_manager.read_json(CLIENT_FILE)
        self.client_id = data['client_id']
        self.secret = data['client_secret']
        self.time_out_limit = 5
        self.headers = None

    def request(self, request_type, link, **kwargs):
        time_out = 0.1
        resp = None
        while True:
            try:
                resp = requests.__dict__[request_type](link, **kwargs)
            except Exception as e:
                exit_util(e.args[0])
            if resp.status_code >= 500:
                time.sleep(time_out)
                time_out += time_out
                continue
            if resp.status_code >= 400:
                exit_util("Something went wrong.")
            if resp:
                return resp
            if time_out > self.time_out_limit:
                exit_util("Time limit connection.")

    def post_request(self, link, **kwargs):
        return self.request("post", link, **kwargs)

    def get_request(self, link, **kwargs):
        return self.request("get", link, **kwargs)

    def update_client(self):
        auth = requests.auth.HTTPBasicAuth(self.client_id, self.secret)
        resp = self.post_request('https://stepic.org/oauth2/token/',
                             data={'grant_type': 'client_credentials'}, auth=auth)
        token = (resp.json())['access_token']
        self.headers = {'Authorization': 'Bearer ' + token, "content-type": "application/json"}

    def get_lesson(self, lesson_id):
        self.update_client()
        lesson = self.get_request(STEPIC_URL + "/lessons/{}".format(lesson_id), headers=self.headers)
        return lesson.json()

    def get_submission(self, attempt_id):
        self.update_client()
        resp = self.get_request(STEPIC_URL + "/submissions/{}".format(attempt_id), headers=self.headers)
        return resp.json()

    def get_attempt_id(self, lesson, step_id):
        self.update_client()
        steps = None
        try:
            steps = lesson['lessons'][0]['steps']
        except Exception:
            exit_util("Didn't receive such lesson.")
        if len(steps) < step_id or step_id < 1:
            exit_util("Too few steps in the lesson.")
        step_id = steps[step_id - 1]
        attempt = {"attempt": {"step": str(step_id)}}
        attempt = self.post_request(STEPIC_URL + "/attempts", data=json.dumps(attempt), headers=self.headers)
        attempt = attempt.json()
        try:
            return attempt['attempts'][0]['id']
        except Exception:
            exit_util("Wrong attempt")
        return None

    def get_submit(self, url, data):
        self.update_client()
        resp = self.post_request(url, data=data, headers=self.headers)
        return resp.json()


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

    def write_json(self, filename, data):
        filename = self.get_name(filename)
        with open(filename, "w") as file:
            json.dump(data, file)

    def read_json(self, filename):
        filename = self.get_name(filename)
        return json.loads(open(filename).read())


def exit_util(message):
    click.secho(message, fg="red")
    sys.exit(0)


programming_language = {'cpp': 'c++11', 'c': 'c++11', 'py': 'python3',
                        'java': 'java8', 'hs': 'haskel 7.10', 'sh': 'shell',
                        'r': 'r'}
                        
                        
def set_client(cid, secret):
    data = file_manager.read_json(CLIENT_FILE)
    if cid:
        data['client_id'] = cid
    if secret:
        data['client_secret'] = secret
    file_manager.write_json(CLIENT_FILE, data)

        
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
    request_inf = stepic_client.get_request(problem_url)
    click.secho("\nSetting connection to the page..", bold=True)
    lesson_id = get_lesson_id(problem_url)
    step_id = get_step_id(problem_url)

    if lesson_id is None or not step_id:
        exit_util("The link is incorrect.")

    lesson = stepic_client.get_lesson(lesson_id)
    attempt_id = stepic_client.get_attempt_id(lesson, step_id)
    try:
        file_manager.write_to_file(ATTEMPT_FILE, str(attempt_id))
    except Exception as e:
        exit_util("You do not have permission to perform this action.")
    click.secho("Connecting completed!", fg="green")


def evaluate(attempt_id):
    click.secho("Evaluating", bold=True, fg='white')
    time_out = 0.1
    while True:
        result = stepic_client.get_submission(attempt_id)
        status = result['submissions'][0]['status']
        hint = result['submissions'][0]['hint']
        if status != 'evaluation':
            break
        click.echo("..", nl=False)
        time.sleep(time_out)
        time_out += time_out
    click.echo("")
    click.secho("You solution is {}\n{}".format(status, hint), fg=['red', 'green'][status == 'correct'])


def submit_code(code):
    file_name = code
    try:
        code = "".join(open(code).readlines())
    except FileNotFoundError:
        exit_util("FIle {} not found".format(code))
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
    submit = stepic_client.get_submit(url, json.dumps(submission))
    evaluate(submit['submissions'][0]['id'])


@click.group()
@click.version_option()
def main():
    """
    Submitter 0.2
    Tools for submitting solutions to stepic.org
    """
    global file_manager
    file_manager = FileManager()
    try:
        file_manager.create_dir(APP_FOLDER)
    except OSError:
        exit_util("Can't do anything. Not enough rights to edit folders.")
    lines = 0
    try:
        data = file_manager.read_json(CLIENT_FILE)
        lines += 1
    except Exception:
        pass
    if lines < 1:
        file_manager.write_json(CLIENT_FILE, {"client_id": "id", "client_secret": "secret"})
    global stepic_client
    stepic_client = StepicClient(FileManager())


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