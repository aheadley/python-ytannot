python-ytannot
==============

Python module and scripts for converting annotations to subtitles.

The ytannot module can be used to download and convert YouTube annotations on videos
into subtitle files (SRT only supported for now, ASS/SSA support planned). Currently
at pre-alpha quality but it does work for the one video I tested on.

Usage is something like:

    $ youtube-dl -q -o 'video.flv' 'http://www.youtube.com/watch?v=<video_id>'
    $ python get-srt-subs.py 'http://www.youtube.com/watch?v=<video_id>' > video.srt
    $ mplayer video.flv
