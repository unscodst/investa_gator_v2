import lxml.html
import requests
from unidecode import unidecode
import time
import random
import datetime
import json
from textblob.classifiers import NaiveBayesClassifier as NBC
from textblob.classifiers import DecisionTreeClassifier as DTC
from textblob import TextBlob
import os
import pickle
from models import CRUD,Ads,TrainData,KeyWords
from sklearn.metrics.pairwise import linear_kernel
from sklearn.feature_extraction.text import TfidfVectorizer

#a web scraper, for local computation
#At present, this seems to work fine
class Scraper:
    def __init__(self,
                 place=None,
                 base_urls=[
                     "http://newyork.backpage.com/FemaleEscorts/",
                     "http://newyork.backpage.com/BodyRubs/",
                     "http://newyork.backpage.com/Strippers/",
                     "http://newyork.backpage.com/Domination/",
                     "http://newyork.backpage.com/TranssexualEscorts/",
                     "http://newyork.backpage.com/MaleEscorts/",
                    "http://newyork.backpage.com/Datelines/",
                     "http://newyork.backpage.com/AdultJobs/"
                 ],
    ):
        if place:
            self.base_urls = self.map_place(place)
        else:
            self.base_urls = base_urls

    def update_place(self,place):
        self.base_urls = self.map_place(place)

    #ToDo, iterate to pages further back in time.
    def generate_pages(self,url):
        urls = []
        init_endings = [
            "FemaleEscorts/",
            "BodyRubs/",
            "Strippers/",
            "Domination/",
            "TranssexualEscorts/",
            "MaleEscorts/",
            "Datelines/",
            "AdultJobs/"
        ]
        init_urls = []
        for ending in endings:
            init_urls.append(url+ending)
        for i in xrange(1,6):
            for url in init_urls:
                urls.append(url+"?page="+str(i))
        urls = init_urls + urls
        return urls
    
    def map_place(self,place):
        places = {
            "alabama":self.generate_pages("http://alabama.backpage.com/")
            "manhattan":self.generate_pages("http://manhattan.backpage.com/"),
            "new york":self.generate_pages("http://newyork.backpage.com/"),
            "new york city":self.generate_pages("http://manhattan.backpage.com/")+self.generate_pages("http://statenisland.backpage.com/")+self.generate_pages("http://queens.backpage.com/")+self.generate_pages("http://brooklyn.backpage.com/")+self.generate_pages("http://bronx.backpage.com/")
            "buffalo":self.generate_pages("http://buffalo.backpage.com/"),
            "albany new york":self.generate_pages("http://albany.backpage.com/"),
            "binghamton":self.generate_pages("http://binghamton.backpage.com/"),
            "catskills":self.generate_pages("http://catskills.backpage.com/"),
            "chautauqua":self.generate_pages("http://chautauqua.backpage.com/"),
            "elmira":self.generate_pages("http://elmira.backpage.com/"),
            "fairfield":self.generate_pages("http://fairfield.backpage.com/"),
            "fingerlakes":self.generate_pages("http://fingerlakes.backpage.com/"),
            "glens falls":self.generate_pages("http://glensfalls.backpage.com/"),
            "hudson valley":self.generate_pages("http://hudsonvalley.backpage.com/"),
            "ithaca":self.generate_pages("http://ithaca.backpage.com/"),
            "long island":self.generate_pages("http://longisland.backpage.com/"),
            "oneonta":self.generate_pages("http://oneonta.backpage.com/"),
            "plattsburgh":self.generate_pages("http://plattsburgh.backpage.com/"),
            "potsdam":self.generate_pages("http://plattsburgh.backpage.com/"),
            "rochester":self.generate_pages("http://plattsburgh.backpage.com/"),
            "syracuse":self.generate_pages("http://plattsburgh.backpage.com/"),
            "twintiers":self.generate_pages("http://twintiers.backpage.com/"),
            "utica":self.generate_pages("http://utica.backpage.com/"),
            "watertown":self.generate_pages("http://watertown.backpage.com/"),
            "westchester":self.generate_pages("http://watertown.backpage.com/")
        }
        
    def letter_to_number(self,text):
        text= text.upper()
        text = text.replace("ONE","1")
        text = text.replace("TWO","2")
        text = text.replace("THREE","3")
        text = text.replace("FOUR","4")
        text = text.replace("FIVE","5")
        text = text.replace("SIX","6")
        text = text.replace("SEVEN","7")
        text = text.replace("EIGHT","8")
        text = text.replace("NINE","9")
        text = text.replace("ZERO","0")
        return text

    def verify_phone_number(self,number):
        data = pickle.load(open("twilio.creds","r"))
        r = requests.get("http://lookups.twilio.com/v1/PhoneNumbers/5165789423",auth=data)
        if "status_code" in json.loads(r.content).keys():
            return False
        else:
            return True
        
    def phone_number_parse(self,values):
        phone_numbers = []
        text = self.letter_to_number(values["text_body"])
        phone = []
        counter = 0
        found = False
        possible_numbers = []
        for ind,letter in enumerate(text):
            if letter.isdigit():
                phone.append(letter)
                found = True
            else:
                if found:
                    counter += 1
                if counter > 15 and found:
                    phone = []
                    counter = 0
                    found = False

            if len(phone) == 10 and phone[0] != '1':
                possible_numbers.append(''.join(phone))
                phone = [] #consider handling measurements
            if len(phone) == 11 and phone[0] == '1':
                possible_numbers.append(''.join(phone))
                phone = [] #consider handling measurements
        for number in possible_numbers:
            if self.verify_phone_number(number):
                phone_numbers.append(number)
        return phone_numbers

    def investigate(self):
        
        data = self.scrape(self.base_urls)
        for datum in data:
            train_crud = CRUD("sqlite:///database.db",Ads,"ads")
            #getting dummy data from http://www.dummytextgenerator.com/#jump
            dummy_crud = CRUD("sqlite:///database.db",TrainData,"training_data")
            train = train_crud.get_all()
            dummy = dummy_crud.get_all()
            train = [(elem.text,"trafficking") for elem in train] + [(elem.text,"not trafficking") for elem in dummy]
            cls = []
            #make use of tdf-idf here
            cls.append(NBC(train))
            cls.append(DTC(train))
            for cl in cls:
                if cl.classify(datum["text_body"]) == "trafficking":
                    self.save_ads([datum])
            

                    
    def scrape(self,links=[],translator=False):
        responses = []
        values = {}
        data = []
        
        for link in links:
            r = requests.get(link)
            text = unidecode(r.text)
            html = lxml.html.fromstring(text)

            links = html.xpath("//div[@class='cat']/a/@href")
            for link in links:
                if len(self.base_urls) > 1 or len(self.base_urls[0]) > 3:
                    time.sleep(random.randint(5,27))
                try:
                    responses.append(requests.get(link))
                    print link
                except requests.exceptions.ConnectionError:
                    print "hitting connection error"
                    continue
                
        for r in responses:
            text = r.text
            html = lxml.html.fromstring(text)
            values["title"] = html.xpath("//div[@id='postingTitle']/a/h1")[0].text_content()
            values["link"] = unidecode(r.url)
            values["new_keywords"] = []
            try:
                values["images"] = html.xpath("//img/@src")
            except IndexError:
                values["images"] = "weird index error"
            pre_decode_text = html.xpath("//div[@class='postingBody']")[0].text_content().replace("\n","").replace("\r","")  
            values["text_body"] = pre_decode_text 
            try:
                values["posted_at"] = html.xpath("//div[class='adInfo']")[0].text_content().replace("\n"," ").replace("\r","")
            except IndexError:
                values["posted_at"] = "not given"
            values["scraped_at"] = str(datetime.datetime.now())
            body_blob = TextBlob(values["text_body"])
            title_blob = TextBlob(values["title"])
            values["language"] = body_blob.detect_language() #requires the internet - makes use of google translate api
            values["polarity"] = body_blob.polarity
            values["subjectivity"] = body_blob.sentiment[1]
            if values["language"] != "en" and not translator:
                values["translated_body"] = body_blob.translate(from_lang="es")
                values["translated_title"] = title_blob.translate(from_lang="es")
            else:
                values["translated_body"] = "none"
                values["translated_title"] = "none"
            text_body = values["text_body"]
            title = values["title"]
            values["phone_numbers"] = self.phone_number_parse(values)
            data.append(values)
        
        return data

    def initial_scrape(self,links):
        data = self.scrape(links)
        self.save_ads(data)
        
    def pull_keywords(self,text):
        """This method should remove any very common english words like 
        the, and and other statistically common words for english language"""
        pass

    def save_ads(self,data):
        crud = CRUD("sqlite:///database.db",table="ads")
        
        for datum in data:
            ad = Ads()
            ad.title=datum["title"],
            ad.phone_numbers=json.dumps(datum["phone_numbers"]),
            ad.text_body=datum["text_body"],
            ad.photos=json.dumps(datum["images"]),#change this so I'm saving actual pictures to the database.
            ad.link=datum["link"],
            ad.posted_at = datum["posted_at"],
            ad.scraped_at=datum["scraped_at"],
            ad.language=datum["language"],
            ad.polarity=datum["polarity"],
            ad.translated_body=datum["translated_body"],
            ad.translated_title=datum["translated_title"],
            ad.subjectivity=datum["subjectivity"],
            crud.insert(ad)
        
if __name__ == '__main__':
    scraper = Scraper(base_urls=["http://newyork.backpage.com/FemaleEscorts/"])
    data = scraper.scrape()
    
    
