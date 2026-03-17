#!/bin/bash

coverage run --omit='tests/unit_tests/*' -m unittest discover -s tests/unit_tests; coverage html
