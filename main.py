#!/usr/bin/env python
# -*- coding: utf-8 -*-
from peewee import Database, SqliteDatabase
import praw
import facebook
from twitter import Twitter, OAuth
from pprint import pprint
import requests
import os
from config import settings
from models import Post, Comment
from typing import Dict, Any

class RedditToTwitterAndFacebook:
    def __init__(self, settingsinst : Dict[str,object]):
        self.db : Database = None 
        self.options(settingsinst or settings)

    def submission_whitelisted(self, submission: praw.models.Submission):
        return submission.author in self.whitelisted_authors

    def submission_offtopic(self, submission: praw.models.Submission):
        return submission.link_flair_text and "offtopic" in submission.link_flair_text or False

    def submission_upvoted(self, submission: praw.models.Submission):
        return submission.is_self and submission.ups >= (self.necessary_upvotes*1.8) \
            or (not submission.is_self and submission.ups >= self.necessary_upvotes)

    def submission_blacklisted(self, submission: praw.models.Submission):
        return submission.author in self.blacklisted_authors
        
    def publish_tw(self, submission: praw.models.Submission):
        # https://github.com/sixohsix/twitter
        try:
            t = Twitter(auth = OAuth(
                                self.tw_token, 
                                self.tw_token_secret, 
                                self.tw_consumer_key, 
                                self.tw_consumer_secret))

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
    
    def publish_fb(self, submission: praw.models.Submission):
        """https://facebook-sdk.readthedocs.io/en/latest/
        how to get a permanent page access token
        http://stackoverflow.com/questions/17197970/facebook-permanent-page-access-token
        """
        try:
            # TODO - fails to post facebook links back to FB    
            graph = facebook.GraphAPI(access_token=self.fb_page_permanent_access_token, 
                                    version=self.fb_graphapi_version)
            attachment = {
                #"name": submission, # filled automatically with title under the url
                "link": submission.url,
                "caption": submission.link_flair_text and submission.link_flair_text.upper() or "",
                #"description": submission.link_flair_text.upper(), # filled automatically from url metadata
                #"picture": "https://www.example.com/thumbnail.jpg" # filled automatically from url
            }
            msg = submission.title + "\n\n💬 https://www.reddit.com" + submission.permalink

            graph.put_wall_post(
                                message=msg, 
                                attachment=attachment, 
                                profile_id=self.fb_page_profile_id
                            )
            print("POSTED TO FB:", msg)
            return True
        except Exception as E:
            print("FB ERROR", E)
            return False


    def init_db(self):
        """Only really needs to be executed the first time the script is running"""
        try:
            self.db = SqliteDatabase(self.sqlite_db_filename)
            self.db.connect()
            if not Post.table_exists():
                db.create_tables([Post,])
            if not Comment.table_exists():
                db.create_tables([Comment,])
        except Exception as E:
            print("DB problem:", E)

    def validate_and_repost_submissions(self):
        """http://praw.readthedocs.io/en/latest/getting_started/quick_start.html"""

        for submission in self.reddit.subreddit(self.reddit_subreddit_name).new(limit=self.reddit_post_limit):
            # just a flag to prevent unnecessary re-saving
            modified = False
            
            # try to find existing db entry for this submission to see if it was already posted
            posts = Post.select().where(Post.urlid == submission.id)
            post = post and posts.get() or None

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
            if not post:
                modified = True
                post = Post.create(urlid = submission.id, 
                                    text = submission.title,
                                    created = submission.created,
                                    author = submission.author,
                                    published_tw = False,
                                    published_fb = False)
                print("SUBMISSION WILL BE SAVED IN DB")

            # if the submission wasn"t reposted to Twitter yet, try to post it
            if not post.published_tw:        
                post.published_tw = publish_tw(submission)
                if post.published_tw: modified = True

            # if the submission wasn"t reposted to Facebook yet, try to post it            
            if not post.published_fb:
                post.published_fb = publish_fb(submission)
                if post.published_fb: modified = True                
            
            if modified: post.save()
            
            print("SUBMISSION STATE:", post, "\n")

    def main(self):
        options = Options()
        self.init_db()
        Post.bind(self.db)
        Comment.bind(self.db)
        self.reddit = praw.Reddit(client_id=self.reddit_client_id,
                            client_secret=self.reddit_client_secret,
                            user_agent=self.reddit_app_user_agent)

        self.validate_and_repost_submissions()

    def options(self, settings):
        self.fb_page_permanent_access_token = os.getenv("FB_PAGE_PERMANENT_ACCESS_TOKEN") or settings["fb_page_permanent_access_token"]
        self.fb_page_profile_id = os.getenv("FB_PAGE_PROFILE_ID") or settings["fb_page_profile_id"]
        self.fb_graphapi_version = os.getenv("FB_GRAPHAPI_VERSION") or settings["fb_graphapi_version"]

        self.reddit_subreddit_name = os.getenv("SUBREDDIT_NAME") or settings["reddit_subreddit_name"]
        self.whitelisted_authors = os.getenv("WHITELISTED_AUTHORS") and os.environ["WHITELISTED_AUTHORS"].split(";") or settings["whitelisted_authors"]
        self.blacklisted_authors = os.getenv("BLACKLISTED_AUTHORS") and os.environ["BLACKLISTED_AUTHORS"].split(";") or settings["blacklisted_authors"]
        self.necessary_upvotes = os.getenv("NECESSARY_UPVOTES") and int(os.environ["NECESSARY_UPVOTES"]) or settings["necessary_upvotes"]
        self.reddit_post_limit = os.getenv("REDDIT_POST_LIMIT") and int(os.environ["REDDIT_POST_LIMIT"]) or settings["reddit_post_limit"]
        self.reddit_client_id = os.getenv("REDDIT_CLIENT_ID") or settings["reddit_client_id"]
        self.reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET") or settings["reddit_client_secret"]
        self.reddit_app_user_agent = os.getenv("REDDIT_APP_USER_AGENT") or settings["reddit_app_user_agent"]

        self.tw_token = os.getenv("TW_TOKEN") or settings["tw_token"]
        self.tw_token_secret = os.getenv("TW_TOKEN") or settings["tw_token_secret"]
        self.tw_consumer_key = os.getenv("TW_TOKEN") or settings["tw_consumer_key"]
        self.tw_consumer_secret = os.getenv("TW_TOKEN") or settings["tw_consumer_secret"]

        self.sqlite_db_filename = os.getenv("SQLITE_DB_FILENAME") or settings["sqlite_db_filename"]

if __name__== "__main__":
    instance = RedditToTwitterAndFacebook()
    instance.main()