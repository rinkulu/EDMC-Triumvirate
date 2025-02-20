
#coding=utf-8

import tkinter as tk
from tkinter import Frame
 
import uuid
from ttkHyperlinkLabel import HyperlinkLabel
import requests
import json
import re
import myNotebook as nb
from .lib.conf import config
#from config import config
import threading
from .debug import debug
from .debug import debug,error
'''
{ "timestamp":"2019-04-29T19:27:30Z", 
"event":"ShipTargeted", 
"TargetLocked":true, 
"Ship":"krait_mkii", 
"Ship_Localised":"Krait Mk II", 
"ScanStage":3, 
"PilotName":"$cmdr_decorate:#name=GromoZekka;", 
"PilotName_Localised":"КМДР GromoZekka", 
"PilotRank":"Elite", 
"SquadronID":"EGPU", 
"ShieldHealth":78.094543, 
"HullHealth":36.569859, 
"LegalStatus":"Clean" }

{ "timestamp":"2019-04-28T20:48:48Z", 
"event":"ShipTargeted", 
"TargetLocked":true, 
"Ship":"orca", 
"ScanStage":3, 
"PilotName":"$npc_name_decorate:#name=Pit Thomsen;",
"PilotName_Localised":"Pit Thomsen", 
"PilotRank":"Dangerous", 
"ShieldHealth":100.000000, 
"HullHealth":100.000000, 
"Faction":"Clayakarma Electronics Limited", 
"LegalStatus":"Clean" }

Заметка №1 отсеивать неписей стоит по конструкции "PilotName":"$npc_name_decorate:#name=Pit Thomsen;", где параметром, прямо указывающим на НПСишность является $npc_name_decorate
Заметка №1.2 стоит посмотреть, как определяются нпс пилоты истребителей
Заметка №2 скорее всего, проще всего определять имя пилота по той же строке, что и неписей
Заметка №2.1 имеет смысл убирать #name= через строчные функции
Заметка №3 модуль не должно быть видно, пока нет данных. так же как это реализовано в release.py
'''

REFRESH_CYCLES = 60 ## how many cycles before we refresh
NEWS_CYCLE = 60 * 1000 # 60 seconds
DEFAULT_NEWS_URL = 'https://vk.com/close_encounters_corps'
WRAP_LENGTH = 200


def _callback(matches):
    id = matches.group(1)
    try:
        return chr(int(id))
    except:
        return id

class UpdateThread(threading.Thread):
    def __init__(self,widget):
        threading.Thread.__init__(self)
        self.widget = widget
    
    def run(self):
        debug('News: UpdateThread')
        # download cannot contain any
        # tkinter changes
        self.widget.download()
        
        

def decode_unicode_references(data):
    return re.sub('&#(\d+)(;|(?=\s))', _callback, data)

class NewsLink(HyperlinkLabel):

    def __init__(self, parent):

        HyperlinkLabel.__init__(self,
            parent,
            text="Получение новостей...",
            url=DEFAULT_NEWS_URL,
            wraplength=50,  # updated in __configure_event below
            anchor=tk.NW)
        self.bind('<Configure>', self.__configure_event)

    def __configure_event(self, event):
        'Handle resizing.'

        self.configure(wraplength=event.width)




class FriendFoe(Frame):

    def __init__(self, parent,gridrow):
        'Initialise the ``News``.'

        padx, pady = 10, 5  # formatting
        sticky = tk.EW + tk.N  # full width, stuck to the top
        anchor = tk.NW        
        
        Frame.__init__(self,
            parent)

        self.hidden = tk.IntVar(value=config.getint('HideFF'))                
        
        self.news_data = []
        self.columnconfigure(1, weight=1)
        self.grid(row = gridrow, column = 0, sticky='NSEW',columnspan=2)
        
        self.label = tk.Label(self, text=  'История целей:')
        self.label.grid(row = 0, column = 0, sticky=sticky)
        self.label.bind('<Button-1>',self.click_news)
        
        self.hyperlink = NewsLink(self)
        self.hyperlink.grid(row = 0, column = 1,sticky='NSEW')
        
        self.news_count = 0
        self.news_pos = 1
        self.minutes = 0
        self.visible()
        #self.hyperlink.bind('<Configure>',
        #self.hyperlink.configure_event)
        self.after(250, self.news_update)
    
    def news_update(self):
    
        if self.isvisible:
        
            if self.news_count == self.news_pos:           
                self.news_pos = 1
            else:
                self.news_pos+=1
            
            if self.minutes == 0:
                UpdateThread(self).start()
            else:
                self.minutes+=-1        

        self.update()                 
        #refesh every 60 seconds
        self.after(NEWS_CYCLE, self.news_update)

    def update(self):
        if self.visible():
            if self.news_data:
                    feed = self.news_data.content.split("\r\n")
                    lines = feed[self.news_pos]
                    news = lines.split("\t")
                    self.hyperlink['url'] = news[1]
                    self.hyperlink['text'] = decode_unicode_references(news[2])
                    debug("News debug" + str(news))
            else:
                #keep trying until we
                #have some data
                #elf.hyperlink['text']
                #= 'Fetching News...'
                self.after(1000, self.update)

    def click_news(self,event):
        if self.news_count == self.news_pos:           
            self.news_pos = 1
        else:
            self.news_pos+=1
            
        self.update()
        
    def download(self):
        'Update the news.'
        
        if self.isvisible:
        
            debug('Fetching FF')
            self.news_data = requests.get('https://docs.google.com/spreadsheets/d/1UnrH5ULSycKzySonUDA79aPBqxUbvNOEOSlW85NY1a0/export?&format=tsv')
            debug(self.news_data)
            #self.news_count=len(self.news_data)-1
            self.news_count = 5
            self.news_pos = 1
            self.minutes = REFRESH_CYCLES

    def plugin_prefs(self, parent, cmdr, is_beta,gridrow):
        'Called to get a tk Frame for the settings dialog.'

        self.hidden = tk.IntVar(value=config.getint('HideFF'))
        
        #frame = nb.Frame(parent)
        #frame.columnconfigure(1,
        #weight=1)
        return nb.Checkbutton(parent, text='Скрыть Систему свой чужой', variable=self.hidden).grid(row = gridrow, column = 0,sticky='NSEW')
        
        #return frame

    def visible(self):
        if self.hidden.get() == 1:
            self.grid_remove()
            self.isvisible = False
            return False
        else:
            self.grid()
            self.isvisible = True
            return True

    def prefs_changed(self, cmdr, is_beta):
        'Called when the user clicks OK on the settings dialog.'
        config.set('HideFF', self.hidden.get())      
        if self.visible():
            self.news_update()
