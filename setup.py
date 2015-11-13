from setuptools import setup

setup(
    name='submitter',
    version='0.1',
    py_modules=['submitter'],
    install_requires=[
        'Click',
	'requests',
	'colorama',
    ],
    entry_points='''
        [console_scripts]
        submitter=submitter:main
    ''',
)
