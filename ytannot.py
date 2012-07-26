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
    atts = None

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
        events = sorted(self._events, key=lambda e: e['start'])
        for i in range(len(events)):
            events[i]['index'] = i+1
        return '\n\n'.join(u'{index}\n{start} --> {end}\n{text}'.format(**event) \
            for event in events)

class ASSSubtitler(AbstractSubtitler):
    pass
