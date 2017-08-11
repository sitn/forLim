# -*- coding: utf-8 -*-

import os


def initialize(options):
    '''
    Prepare the folders for outputs:
    '''
    if not os.path.isdir(options['dst']):
        os.mkdir(options['dst'])
    if not options['dst'].endswith('/'):
        options['dst'] = options['dst'] + '/'
    tifdst = options['dst'] + 'tif'
    if not os.path.exists(tifdst):
        os.makedirs(tifdst)
    shpdst = options['dst'] + 'shp'
    if not os.path.exists(shpdst):
        os.makedirs(shpdst)
