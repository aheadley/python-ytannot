import requests
from xml.dom.minidom import parseString

# 1
# 00:02:17,440 --> 00:02:20,375
# Senator, we're making
# our final approach into Coruscant.

ANNOTATION_URL = 'http://www.youtube.com/annotations/read2?feat=TCS&video_id={video_id}'

class NotTextNodeError(Exception): pass

class NodeDict(dict):
    attrs = None

class NodeList(list):
    attrs = None

class StrNode(unicode):
    attrs = None

def xml_node_to_text(node):
    """
    scans through all children of node and gathers the
    text. if node has non-text child-nodes, then
    NotTextNodeError is raised.
    """

    if any(cn.nodeType != cn.TEXT_NODE for cn in node.childNodes):
        raise NotTextNodeError
    else:
        node_str = StrNode(u''.join(cn.nodeValue for cn in node.childNodes))
        if node.attributes is not None and node.attributes.length > 0:
            # node_dict.attrs = dict((a.name, a.value) for a in node.attributes)
            node_str.attrs = {}
            for attr in (node.attributes.item(i) for i in range(node.attributes.length)):
                node_str.attrs[attr.name] = attr.value
        return node_str


def xml_node_to_dict(node):
    """Convert a minidom node to dict"""
    node_dict = NodeDict()
    if node.attributes is not None and node.attributes.length > 0:
        # node_dict.attrs = dict((a.name, a.value) for a in node.attributes)
        node_dict.attrs = {}
        for attr in (node.attributes.item(i) for i in range(node.attributes.length)):
            node_dict.attrs[attr.name] = attr.value
    for cn in (n for n in node.childNodes if n.nodeType == n.ELEMENT_NODE):
        try:
            cn_content = xml_node_to_text(cn)
        except NotTextNodeError:
            cn_content = xml_node_to_dict(cn)
        if cn.nodeName in node_dict:
            try:
                node_dict[cn.nodeName].append(cn_content)
            except AttributeError:
                node_dict[cn.nodeName] = NodeList([node_dict[cn.nodeName], cn_content])
        else:
            node_dict[cn.nodeName] = cn_content
    return node_dict

def xml_to_dict(xml_string):
    """Convert XML data to a Python dict"""
    return xml_node_to_dict(parseString(xml_string))


class AnnotationParser(object):
    def __init__(self, formatter):
        self._sub_formatter = formatter

    def _get_annotations(self, video_id):
        return requests.get(ANNOTATION_URL.format(video_id=video_id)).text.encode('utf-8')

    def _parse_annotations(self, content):
        return xml_to_dict(content)

    def format(self, content=None, video_id=None):
        if content is None:
            if video_id is None:
                raise Exception
            else:
                content = self._get_annotations(video_id)
        annot_struct = self._parse_annotations(content)
        for event in (e for e in annot_struct['document']['annotations']['annotation'] if e.get('TEXT', False)):
            try:
                region = event['segment']['movingRegion']['rectRegion']
            except KeyError:
                region = event['segment']['movingRegion']['anchoredRegion']
            start_ts = region[0].attrs['t']
            end_ts = region[1].attrs['t']
            if start_ts != 'never' and end_ts != 'never':
                self._sub_formatter.create_event(
                    text=event['TEXT'],
                    start='0'+start_ts.replace('.', ','),
                    end='0'+end_ts.replace('.', ','),
                )

        return self._sub_formatter.generate()

class AbstractSubtitler(object):
    def __init__(self):
        self._events = []

    def generate(self):
        pass

    def add_event(self, event):
        self._events.append(event)

    def create_event(self, **kwargs):
        self._events.append(kwargs)

    @property
    def duration(self):
        pass


class SRTSubtitler(AbstractSubtitler):
    def generate(self):
        return '\n\n'.join(u'{index}\n{start} --> {end}\n{text}'.format(
            index=i+1,
            start=self._format_ts(event['start']),
            end=self._format_ts(event['end']),
            text=event['text']) for i, event in \
                enumerate(sorted(self._events, key=lambda e: e['start'])))

    def _format_ts(self, ts):
        return '{0:02d}:{1:02d}:{2:02d},{3:03d}'.format(
            *map(int, ts.replace(',', ':').split(':')))

class ASSSubtitler(AbstractSubtitler):
    def generate(self):
        #totally copied from [Mazui]'s Hyouka 14
        content = """[Script Info]
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
Collisions: Normal
Scroll Position: 0
Active Line: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,51,&H00FFFFFF,&H000000FF,&H0004090F,&HB40C131C,-1,0,0,0,101,100,0.3,0,1,2.8,1,2,120,120,35,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        return content + '\n'.join(self._format_event(event) for event in self._events)

    def _format_event(self, event):
        return u'Dialogue: 0,{start},{end},Default,,0000,0000,0000,,{text}'.format(
            start=self._format_ts(event['start']),
            end=self._format_ts(event['end']),
            text=' '.join(l.strip() for l in event['text'].split('\n')))

    def _format_ts(self, ts):
        return '{0:02d}:{1:02d}:{2:02d}.{3:02d}'.format(
            *map(int, ts.replace(',', ':').split(':')))
