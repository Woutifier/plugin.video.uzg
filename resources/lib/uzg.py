'''
    resources.lib.uzg
    ~~~~~~~~~~~~~~~~~

    An XBMC addon for watching Uitzendinggemist(NPO)
   
    :license: GPLv3, see LICENSE.txt for more details.

    Uitzendinggemist (NPO) = Made by Bas Magre (Opvolger)    
    based on: https://github.com/jbeluch/plugin.video.documentary.net

'''
import urllib2 ,re ,time ,json
from datetime import datetime
from HTMLParser import HTMLParser
from urlparse import urljoin

# create a subclass and override the handler methods
class MyHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.episodes = []
        self._current_episode = None
        self.expect_title = False

    def handle_starttag(self, tag, attrs):
        classattr = next(iter([x[1] for x in attrs if x[0] == "class"]), None)
        if tag == "div" and classattr is not None and "npo-asset-tile-container" in classattr:
            self.depthcount = 0
            self._current_episode = {
                'label': "",
                'date': None,
            }
        if tag == "a":
            hrefattr = next(iter([x[1] for x in attrs if x[0] == "href"]), None)
            if hrefattr is not None:
                match = re.search("([0-9]{1,2}-[0-9]{1,2}-[0-9]{4})", hrefattr)
                if match:
                    parsed_date = None
                    try:
                        parsed_date = datetime.strptime(match.group(1), "%d-%m-%Y")
                    except TypeError:
                        parsed_date = datetime(*(time.strptime(match.group(1), "%d-%m-%Y")[0:6]))
                    self._current_episode['date'] = parsed_date.strftime('%Y-%m-%dT%H:%M:%S')
                    self._current_episode['TimeStamp'] = self._current_episode['date']
                match = re.search("/([A-Z]+_[0-9]+)$", hrefattr)
                if match:
                    self._current_episode['whatson_id'] = match.group(1)
        if tag == "h2":
            self.expect_title = True
        if tag == "img":
            srcattr = next(iter([x[1] for x in attrs if x[0] == "src"]), None)
            if srcattr is not None:
                self._current_episode['thumbnail'] = srcattr
        if tag == "div" and self.depthcount is not None:
            self.depthcount += 1

    def handle_endtag(self, tag):
        if tag == "h2":
            self.expect_title = False
        if tag == "div" and self.depthcount is not None:
            self.depthcount -= 1
        if self.depthcount == 0:
            self.episodes.append(self._current_episode)
            self._current_episode = None
            self.depthcount = None

    def handle_data(self, data):
        if self.expect_title:
            self._current_episode['label'] += data

class Uzg:
        #
        # Init
        #
        def __init__( self):
            self.overzichtcache = 'leeg'
            self.items = 'leeg'            

        def __overzicht(self):        
            req = urllib2.Request('http://apps-api.uitzendinggemist.nl/series.json')
            req.add_header('User-Agent', 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:25.0) Gecko/20100101 Firefox/25.0')
            response = urllib2.urlopen(req)
            link=response.read()
            response.close()
            json_data = json.loads(link)
            uzgitemlist = list()
            for serie in json_data:
                uzgitem = { 'label': serie['name'], 'nebo_id': serie['mid'], 'thumbnail': serie['image'] }
                uzgitemlist.append(uzgitem)                
            self.overzichtcache = sorted(uzgitemlist, key=lambda x: x['label'], reverse=False)

        def __items(self, nebo_id):
            jsondata = self.get_url_data_as_json("https://www.npo.nl/media/series/{}/episodes?page=1&tilemapping=dedicated&tiletype=asset".format(nebo_id))

            #First
            parser = MyHTMLParser()
            parser.feed(jsondata['tiles'])
            episode_list = []
            episode_list.extend(parser.episodes)

            while jsondata['nextLink'] != "":
                url = urljoin("https://www.npo.nl", jsondata['nextLink']+"&tilemapping=dedicated&tiletype=asset")
                jsondata = self.get_url_data_as_json(url)
                parser = MyHTMLParser()
                parser.feed(jsondata['tiles'])
                episode_list.extend(parser.episodes)

            self.items = episode_list

        def get_url_data_as_json(self, url):
            req = urllib2.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:25.0) Gecko/20100101 Firefox/25.0')
            req.add_header('X-Requested-With', 'XMLHttpRequest')
            response = urllib2.urlopen(req)
            data = response.read()
            response.close()
            return json.loads(data)
        # def __items(self, nebo_id):
        #     req = urllib2.Request('http://apps-api.uitzendinggemist.nl/series/'+nebo_id+'.json')
        #     req.add_header('User-Agent', 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:25.0) Gecko/20100101 Firefox/25.0')
        #     response = urllib2.urlopen(req)
        #     link=response.read()
        #     response.close()
        #     json_data = json.loads(link)
        #     uzgitemlist = list()
        #     for aflevering in json_data['episodes']:
        #         urlcover = ''
        #         if not aflevering['stills']:
        #             urlcover = ''
        #         else:
        #             urlcover = aflevering['stills'][0]['url']
        #         uzgitem = { 'label': aflevering['name']
        #                     , 'date': self.__stringnaardatumnaarstring(datetime.fromtimestamp(int(aflevering['broadcasted_at'])).strftime('%Y-%m-%dT%H:%M:%S'))
        #                     , 'TimeStamp': datetime.fromtimestamp(int(aflevering['broadcasted_at'])).strftime('%Y-%m-%dT%H:%M:%S')
        #                     , 'thumbnail': urlcover
        #                     , 'serienaam': json_data['name']
        #                     , 'whatson_id': aflevering['whatson_id']}
        #         uzgitemlist.append(uzgitem)
        #     self.items = uzgitemlist

        def __get_data_from_url(self, url):
            req = urllib2.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:25.0) Gecko/20100101 Firefox/25.0')
            response = urllib2.urlopen(req)
            data=response.read()
            response.close()
            return data    

        def get_ondertitel(self, whatson_id):
            return 'http://apps-api.uitzendinggemist.nl/webvtt/'+whatson_id+'.webvtt'
            
        def get_play_url(self, whatson_id):
            ##token aanvragen
            data = self.__get_data_from_url('http://ida.omroep.nl/app.php/auth')
            token = re.search(r'token\":"(.*?)"', data).group(1)
            ##video lokatie aanvragen
            data = self.__get_data_from_url('http://ida.omroep.nl/app.php/'+whatson_id+'?adaptive&adaptive=yes&part=1&token='+token)
            json_data = json.loads(data)
            ##video file terug geven vanaf json antwoord
            streamdataurl = json_data['items'][0][0]['url']
            streamurl = str(streamdataurl.split("?")[0]) + '?extension=m3u8'
            data = self.__get_data_from_url(streamurl)
            json_data = json.loads(data)
            url_play = json_data['url']
            return url_play
            
        def get_overzicht(self):
            self.items = 'leeg' ##items weer leeg maken
            if (self.overzichtcache == 'leeg'):
                self.__overzicht()
            return self.overzichtcache            


        def get_items(self, nebo_id):
            if (self.items == 'leeg'):
                self.__items(nebo_id)
            return [self.__build_item(i) for i in self.items]
    
        def __build_item(self, post):    
            ##item op tijd gesorteerd zodat ze op volgorde staan.
            if (len(post['label']) == 0):
                titelnaam = post['serienaam']
            else:
                titelnaam = post['label']

            item = {
                'label': '(' + post['TimeStamp'].split('T')[0] + ') - ' + titelnaam,
                'date': post['date'],
                'thumbnail': post['thumbnail'],
                'whatson_id': post['whatson_id'],
            }
            return item

        def __stringnaardatumnaarstring(self, datumstring):
            b = datetime(*(time.strptime(datumstring.split('T')[0], "%Y-%m-%d")[0:6]))
            return b.strftime("%d-%m-%Y")
