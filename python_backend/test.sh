#!/bin/bash
v4l2-ctl --device /dev/video0 -c auto_exposure=1 && v4l2-ctl --device /dev/video0 -c exposure_time_absolute=7
python test.py
