import xml.etree.cElementTree as ET
import codecs
import json
import re
from bson.son import SON

OSMFILE = "wuhan_china.osm"

CREATED = ["version", "changeset", "timestamp", "user", "uid"]

# Usually values for SERVICE are Yes
FACILITY = ["bus", "bench", "shelter", "atm"]

ROAD = ["oneway", "lanes", "bridge", "highway", "tunnel"]

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
    if not rlt:
        # print "F", s
        return False
    # print "T",s, rlt.group()
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
            if tag.attrib['k'] == 'name':  # t == 'name':
                # print tag.attrib['v']
                str_name = ""
                if audit_chinese(tag.attrib['v']):
                    str_name = tag.attrib['v']
                if str_name.endswith(u"\u9053") or str_name.endswith(u"\u8def"):
                    # print str_name
                    road = {}
                    for key in ROAD:
                        q = "./tag[@k='{0}']".format(key)
                        ntags = element.findall(q)
                        for nt in ntags:
                            road[nt.attrib['k']] = nt.attrib['v']
                    if road.__len__ > 0:
                        node["road"] = road
                node["name"] = str_name
            elif t == 'addr':
                if not node.has_key('address'):
                    node['address'] = ADDRESS
                node['address'][v[1]] = tag.attrib['v']
            elif tag.attrib['k'] in FACILITY:
                # print "find facility : %s" % tag.attrib['k']
                srv.append(tag.attrib['k'])
            elif tag.attrib['k'] in KEEP:
                node[tag.attrib['k']] = tag.attrib['v']

        if len(srv) > 0:
            node['facility'] = srv
        node['type'] = element.tag
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


def most_frequent_user():
    return [
        {"$unwind": "$created.user"},
        {"$group": {"_id": "$created.user", "count": {"$sum": 1}}},
        {"$sort": SON([("count", -1), ("_id", -1)])}
    ]


def get_db():
    from pymongo import MongoClient
    client = MongoClient('mongotest.chinanorth.cloudapp.chinacloudapi.cn:27018')
    db = client.test_database
    return db


REGENERATE_DATA = False


def reduce_count(curr, result):
    result.total += 1


def test():
    db = get_db()
    if REGENERATE_DATA:
        data = process_map(OSMFILE)
        print "processed map"
        db.map.insert(data)
        print "inserted data"

    print "Start query..."
    query = id_query("286073600")
    # query = user_query("samsung galaxy s6")
    # query = service_query("atm")
    # query = most_frequent_user()
    nodes = db.map.find(query)
    # nodes = db.map.aggregate(
    #     [{"$limit": 5}, {"$group": {"_id": "$created.user", "count": {"$sum": 1}}}, {"$sort": {"count", -1}}])
    nodes = list(nodes)
    print len(nodes)
    # for node in nodes:
    #     print node


if __name__ == '__main__':
    from pymongo import MongoClient

    test()
