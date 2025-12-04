# -*- coding: utf-8 -*-
# Copyright (c) 2025, BrainWise and contributors
# For license information, please see license.txt

# Import get_build_version from the parent utils.py module
# This is needed because this utils/ package directory shadows the utils.py file
import importlib.util
import os

# Get the parent directory (pos_next)
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_utils_file = os.path.join(_parent_dir, 'utils.py')

if os.path.exists(_utils_file):
    # Load the utils.py file as a module
    spec = importlib.util.spec_from_file_location("pos_next_utils_module", _utils_file)
    _utils_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_utils_module)
    
    # Re-export get_build_version and get_app_version
    get_build_version = _utils_module.get_build_version
    get_app_version = getattr(_utils_module, 'get_app_version', None)
else:
    # Fallback if utils.py doesn't exist
    import time
    def get_build_version():
        return str(int(time.time()))

