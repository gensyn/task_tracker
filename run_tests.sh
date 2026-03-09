#!/bin/bash

coverage run --omit='test/*' -m unittest discover -s test; coverage html
