# Creators.TF Master Server
> What is the Creators.TF Master Server?

The **Creators.TF Master Server** (the third time we've said that now) is a Python Script which queries normal Quickplay, Balancemod, Silly Events and Vanilla+ gameservers on our network. Servers are queried using A2S, and the results are packaged up and sent to the website with an HTTP request.

> This says "Master Server Python", was/is there another version?
Yes, actually. Before this application was made, the Master Server used to be written in JavaScript. The trouble was that it was poorly written, and constantly on life support. Any small change with a library would break it, and it required constant attention and a cronjob to keep alive. This application is a rewrite in Python, so hopefully it doesn't break anymore :pray:

# Installation
This application has a Pipfile that can be used to help install the correct packages and ensure you have the correct Python version. This application was originally coded and tested on Python 3.8.1. If you don't have `pipenv` installed, follow the basic installation guide [here](https://pipenv.pypa.io/en/latest/).

To install from the Pipfile, simply run: `pipenv install`
