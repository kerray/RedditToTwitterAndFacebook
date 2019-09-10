#!/usr/bin/env python
# -*- coding: utf-8 -*-
from peewee import *
import praw
import facebook
from twitter import *
from pprint import pprint
import requests
import os
from config import settings

fb_page_permanent_access_token = os.getenv("FB_PAGE_PERMANENT_ACCESS_TOKEN") or settings["fb_page_permanent_access_token"]
fb_page_profile_id = os.getenv("FB_PAGE_PROFILE_ID") or settings["fb_page_profile_id"]
fb_graphapi_version = os.getenv("FB_GRAPHAPI_VERSION") or settings["fb_graphapi_version"]

reddit_subreddit_name = os.getenv("SUBREDDIT_NAME") or settings["reddit_subreddit_name"]
whitelisted_authors = os.getenv("WHITELISTED_AUTHORS") and os.environ["WHITELISTED_AUTHORS"].split(";") or settings["whitelisted_authors"]
blacklisted_authors = os.getenv("BLACKLISTED_AUTHORS") and os.environ["BLACKLISTED_AUTHORS"].split(";") or settings["blacklisted_authors"]
necessary_upvotes = os.getenv("NECESSARY_UPVOTES") and int(os.environ["NECESSARY_UPVOTES"]) or settings["necessary_upvotes"]
reddit_post_limit = os.getenv("REDDIT_POST_LIMIT") and int(os.environ["REDDIT_POST_LIMIT"]) or settings["reddit_post_limit"]
reddit_client_id = os.getenv("REDDIT_CLIENT_ID") or settings["reddit_client_id"]
reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET") or settings["reddit_client_secret"]
reddit_app_user_agent = os.getenv("REDDIT_APP_USER_AGENT") or settings["reddit_app_user_agent"]

tw_token = os.getenv("TW_TOKEN") or settings["tw_token"]
tw_token_secret = os.getenv("TW_TOKEN") or settings["tw_token_secret"]
tw_consumer_key = os.getenv("TW_TOKEN") or settings["tw_consumer_key"]
tw_consumer_secret = os.getenv("TW_TOKEN") or settings["tw_consumer_secret"]

sqlite_db_filename = os.getenv("SQLITE_DB_FILENAME") or settings["sqlite_db_filename"]
db = SqliteDatabase(sqlite_db_filename)

class Article(Model):
    """Database of articles this script has already processed and their state - have they been posted to FB and TW or not?"""
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
        database = db 

def submission_whitelisted(submission):
    return submission.author in whitelisted_authors

def submission_offtopic(submission):
    return submission.link_flair_text and "offtopic" in submission.link_flair_text or False

def submission_upvoted(submission):
     return submission.is_self and submission.ups >= (necessary_upvotes*1.8) \
         or (not submission.is_self and submission.ups >= necessary_upvotes)

def submission_blacklisted(submission):
    return submission.author in blacklisted_authors
    
def publish_tw(submission):
    """https://github.com/sixohsix/twitter"""
    try:
        t = Twitter(auth = OAuth(tw_token, tw_token_secret, tw_consumer_key, tw_consumer_secret))

        # submission title will be the tweet text - we shorten it and add link to reddit comments                         
        tweet = submission.title
        if len(tweet) > 254: tweet = tweet[0:254] + "…"
        tweet = tweet + "\nhttps://www.reddit.com" + submission.permalink

        t.statuses.update(status=tweet)
        print("TWEET:", tweet)
        return True
    except Exception as E:
        print("TW ERROR", E)        
        return False
 
def publish_fb(submission):
    """https://facebook-sdk.readthedocs.io/en/latest/
    how to get a permanent page access token
    http://stackoverflow.com/questions/17197970/facebook-permanent-page-access-token
    """
    try:
        # TODO - fails to post facebook links back to FB    
        graph = facebook.GraphAPI(access_token=fb_page_permanent_access_token, 
                                  version=fb_graphapi_version)
        attachment = {
            #"name": submission, # filled automatically with title under the url
            "link": submission.url,
            "caption": submission.link_flair_text and submission.link_flair_text.upper() or "",
            #"description": submission.link_flair_text.upper(), # filled automatically from url metadata
            #"picture": "https://www.example.com/thumbnail.jpg" # filled automatically from url
        }
        msg = submission.title + "\n\n💬 https://www.reddit.com" + submission.permalink
        graph.put_wall_post(message=msg, attachment=attachment, profile_id=fb_page_profile_id)
        print("POSTED TO FB:", msg)
        return True
    except Exception as E:
        print("FB ERROR", E)
        return False


def init_db():
    """Only really needs to be executed the first time the script is running"""
    try:
        db.connect()
        if not Article.table_exists():
            db.create_tables([Article,])
    except Exception as E:
        print("DB problem:", E)

def validate_and_repost_submissions():
    """http://praw.readthedocs.io/en/latest/getting_started/quick_start.html"""
    reddit = praw.Reddit(client_id=reddit_client_id,
                         client_secret=reddit_client_secret,
                         user_agent=reddit_app_user_agent)

    for submission in reddit.subreddit(reddit_subreddit_name).new(limit=reddit_post_limit):
        # just a flag to prevent unnecessary re-saving
        modified = False
        
        # try to find existing db entry for this submission to see if it was already posted
        articles = Article.select().where(Article.urlid == submission.id)
        article = articles and articles.get() or None

        print("ENTRY ID:", submission.id, 
              "UPVOTES:", submission.ups, 
              "TITLE:", submission.title)
              
        if submission_blacklisted(submission): 
            print("AUTHOR BLACKLISTED, SKIPPING\n")
            continue
            
        if submission_offtopic(submission): 
            print("SUBMISSION OFFTOPIC, SKIPPING\n")
            continue
            
        if not submission_whitelisted(submission) and not submission_upvoted(submission):
            print("NOT ENOUGH UPVOTES\n")
            continue
        
        # if the submission is whitelisted of reposting and doesn"t exist in db, create it 
        if not article:
            modified = True
            article = Article.create(urlid = submission.id, 
                                     text = submission.title,
                                     created = submission.created,
                                     author = submission.author,
                                     published_tw = False,
                                     published_fb = False)
            print("SUBMISSION WILL BE SAVED IN DB")

        # if the submission wasn"t reposted to Twitter yet, try to post it
        if not article.published_tw:        
            article.published_tw = publish_tw(submission)
            if article.published_tw: modified = True

        # if the submission wasn"t reposted to Facebook yet, try to post it            
        if not article.published_fb:
            article.published_fb = publish_fb(submission)
            if article.published_fb: modified = True                
        
        if modified: article.save()
        
        print("SUBMISSION STATE:", article, "\n")


init_db()

validate_and_repost_submissions()
