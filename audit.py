import xml.etree.cElementTree as ET
import codecs
import json
import re
from datetime import datetime
import time

OSMFILE = "wuhan_china.osm"

CREATED = ["version", "changeset", "timestamp", "user", "uid"]

# Usually values for SERVICE are Yes
FACILITY = ["bench", "shelter", "atm"]

# Keys of address node
ADDRESS = dict.fromkeys(["housenumber", "postcode", "street"], None)

KEEP = [
    "name", "amenity", "cuisine", "tourism", "highway", "historic", "natural",
    "phone",
]

re_words = re.compile(u"[\u4e00-\u9fa5]+")


def get_type(elem):
    '''
    This function takes an element, try to split key with colon. It returns string and array.
    :param elem:
    :return: string, list
    '''
    e_array = elem.attrib['k'].split(':')
    if len(e_array) > 1:
        return e_array[0], e_array
    else:
        return '', elem.attrib['k']


def audit_chinese(s):
    '''
    This function audit if parameter s is pure Chinese character, returns True or False.
    :param s: string
    :return: string
    '''
    s = unicode(s)
    u_chinese = re.compile(u"[\u4e00-\u9fa5]+")
    rlt = u_chinese.search(s, 0)
    if s != rlt:
        return False
    return True


def shape_element(element):
    '''
    This function takes an xml element, transfer it to a JSon dictionary.
    :param element:
    :return:
    '''
    node = {}
    if element.tag == "node" or element.tag == "way":
        srv = []
        for tag in element.iter("tag"):
            t, v = get_type(tag)
            if t == 'name':
                # print tag.attrib['v']
                if audit_chinese(tag.attrib['v']):
                    node[tag.attrib['k']] = audit_chinese(tag.attrib['v'])
                elif len(v) > 1 and v[1] == 'zh':
                    node["name"] = tag.attrib['v']
            elif t == 'addr':
                if not node.has_key('address'):
                    node['address'] = ADDRESS
                node['address'][v[1]] = tag.attrib['v']
            elif tag.attrib['k'] in FACILITY:
                # print "find facility : %s" % tag.attrib['k']
                srv.append(tag.attrib['k'])
            elif tag.attrib['k'] in KEEP:
                node[tag.attrib['k']] = tag.attrib['v']
            else:
                pass

        if len(srv) > 0:
            node['facility'] = srv
        node['type'] = 'node'
        create = {}
        l = [0, 0]
        for attrib in element.attrib:
            if attrib in CREATED:
                create[attrib] = element.attrib[attrib]
            elif attrib in ['id', 'visible']:
                node[attrib] = element.attrib[attrib]
            elif attrib == 'lon':
                l[1] = element.attrib[attrib]
            elif attrib == 'lat':
                l[0] = element.attrib[attrib]
        node['created'] = create
        node['pos'] = l
        return node
    else:
        return None


def process_map(osmfile, pretty=False):
    file_out = "{0}.json".format(osmfile)
    data = []
    with codecs.open(file_out, "w") as fo:
        for event, elem in ET.iterparse(osmfile, events=("start",)):
            el = shape_element(elem)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2) + "\n")
                else:
                    fo.write(json.dumps(el) + "\n")
    return data


def service_query(srv):
    '''
    Gets nodes that contains facility
    :param srv:
    :return:
    '''
    return {"facility": {"$exists": "true"}}


def user_query(user):
    '''
    Gets node by created.user, which is usually a device name.
    :param user:
    :return:
    '''
    return {"created.user": user}


def id_query(id):
    '''
    Gets node by id string
    :param id:
    :return:
    '''
    return {"id": id}


def get_db():
    from pymongo import MongoClient
    client = MongoClient('mongotest.chinanorth.cloudapp.chinacloudapi.cn:27018')
    db = client.test_database
    return db


REGENERATE_DATA = True


def test():
    db = get_db()
    if REGENERATE_DATA:
        data = process_map(OSMFILE)
        print "processed map"
        db.map.insert(data)
        print "inserted data"

    # query = id_query("286073600")
    # query = user_query("samsung galaxy s6")
    query = service_query("atm")
    nodes = db.map.find(query)
    print "nodes.count() : %d" % nodes.count()
    for node in nodes:
        print node


if __name__ == '__main__':
    from pymongo import MongoClient

    test()
