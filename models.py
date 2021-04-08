from peewee import Model, CharField, BooleanField, DateField

class Article(Model):
    """Database of posts this script has already processed and their state - have they been posted to FB and TW or not?"""
    urlid = CharField()
    text = CharField()
    created = DateField()
    author = CharField()
    published_tw = BooleanField()
    published_fb = BooleanField()
    
    def __str__(self):
        r = {}
        for k in self.__data__.keys():
          try:
             r[k] = str(getattr(self, k))
          except:
             r[k] = json.dumps(getattr(self, k))
        return str(r)

    class Meta:
        table_name = "Article" # OBSOLETE - use only for old databases
    

class Comment(Model):
    """Database of comments this script has already processed and their state - have they been posted to FB and TW or not?"""
    urlid = CharField()
    text = CharField()
    created = DateField()
    author = CharField()
    post = ForeignKeyField(Article, 
    published_tw = BooleanField()
    published_fb = BooleanField()
    
    def __str__(self):
        r = {}
        for k in self.__data__.keys():
          try:
             r[k] = str(getattr(self, k))
          except:
             r[k] = json.dumps(getattr(self, k))
        return str(r)
    
