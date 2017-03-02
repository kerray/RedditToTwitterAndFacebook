# RedditToTwitterAndFacebook

This simple Python 3 script loads submissions from a subreddit, validates whether they pass some criteria 
(currently if they have enough upvotes or come from a list of pre-approved users), and posts these 
submissions to a Twitter account and a Facebook Page.

The list of submissions that were already processed resides in SQLite so that every submission gets 
posted just once.

It needs to be set up in a cron job to run periodically, and it also needs access tokens from 
Reddit, Twitter and Facebook to work.

Before runnning, copy config.default.py to config.py and either set up all the required tokens and 
values, or keep it as is and save the values in environment variables.

__Package dependencies__
- praw
- peewee
- git+https://github.com/sixohsix/twitter.git#egg=Twitter
- git+https://github.com/mobolic/facebook-sdk#egg=facebook-sdk

__Future development__
Maybe:
- track post IDs in DB so that they can be later deleted or commented on
- track sticky submissions and pin them to top of page
- repost approved reddit comments to the linked FB post
