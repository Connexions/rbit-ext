# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""\
rbit extensions for integration with oer.exports epub generation code.

"""
import os
import sys
import subprocess
import shutil
import tempfile
import jsonpickle

from . import utils
from .utils import logger


def make_epub(message, set_status, settings={}):
    """rbit extension to interface with the oer.exports epub code.

    Available settings:

    - **output-dir** - Directory where the produced file is stuck.
    - **oer.exports-dir** - Defines the location of the oer.exports package.
    - **python** - Defines which python executable should be used.

    """
    python_executable = settings.get('python', sys.executable)
    oerexports_dir = settings['oer.exports-dir']
    output_dir = settings['output-dir']

    # Start the building sequence by updating the build's status.
    build_request = jsonpickle.decode(message)
    build_request.stamp_request()
    timestamp = build_request.get_buildstamp()
    status_message = "Starting job, timestamp: {0}".format(timestamp)
    set_status('Building', status_message)

    # Create a temporary directory to work in...
    build_dir = tempfile.mkdtemp()
    logger.debug("Working in '{0}'.".format(build_dir))

    # Acquire the collection's data in a collection directory format.
    pkg_name = build_request.get_package()
    version = build_request.get_version()
    base_uri = build_request.transport.uri
    collection_dir = utils.get_completezip(pkg_name, version, base_uri,
                                           build_dir)
    # FIXME We need to grab the version from the unpacked directory
    #       name because 'latest' is only a symbolic name that will
    #       not be used in the resulting filename.
    if version == 'latest':
        # Using the unpacked complete zip filename, with the structure
        #   <id>_<version>_complete, we can parse the version.
        version = collection_dir.split('_')[1]

    # Run the oer.exports script against the collection data.
    build_script = os.path.join(oerexports_dir, 'content2epub.py')
    result_filename = '{0}-{1}.epub'.format(build_request.get_package(),
                                            version)
    result_filepath = os.path.join(build_dir, result_filename)
    command = [python_executable, build_script, collection_dir,
               # The follow are not optional, values must be supplied.
               '-t', 'collection',
               '-c', os.path.join(oerexports_dir, 'static', 'content.css'),
               '-e', os.path.join(oerexports_dir, 'xsl', 'dbk2epub.xsl'),
               '-o', result_filepath,
               ]
    set_status('Building', "Running: " + ' '.join(command))
    process = subprocess.Popen(command,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=build_dir)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        # Something went wrong...
        set_status('Failed', stderr)
        return
    else:
        msg = "EPUB created, moving contents to final destination..."
        set_status('Building', msg)

    # Move the file to it's final destination.
    shutil.copy2(result_filepath, output_dir)
    output_filepath = os.path.join(output_dir, result_filename)
    set_status('Building', "Placing file a location: " + output_filepath)

    # Remove the temporary build directory
    shutil.rmtree(build_dir)

    set_status('Done')
