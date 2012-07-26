#!/usr/bin/env python

import ytannot
import sys
import re

try:
    video_id = re.search(r'v=([^&]+)(?:&|$)', sys.argv[1]).group(1)
except KeyError:
    print 'Missing video URL'
except AttributeError:
    print 'Failed to find video_id from URL'
else:
    a = ytannot.AnnotationParser(ytannot.SRTSubtitler())
    content = a.format(video_id=video_id).encode('utf-8')
    print content + '\n'
