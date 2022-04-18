from instagram_setup import get_client, check_login_status, maybe_login

from instagrapi import Client
from instagrapi.exceptions import DirectThreadNotFound
from datetime import datetime
import logging
import random
import time


logging.getLogger().setLevel(logging.INFO)
logging.getLogger('public_request').setLevel(logging.WARNING)


def get_follower_list(client: Client) -> list:
    """
    Get a list of follower usernames associated with `client`. The first run
    may take a few minutes depending on follower count, but subsequent runs
    in the same session are very fast.

    Parameters
    ----------
    client : instagrapi.Client

    Returns
    -------
    follower_usernames : list of strings, one per follower
    """

    logging.info("Gathing followers – this may take a few minutes")

    start = time.time()
    followers = client.user_followers(client.user_id)
    end = time.time()

    duration = round(end - start)

    logging.info(f"Gathered {len(followers)} followers in ~{duration} seconds")

    follower_usernames = [follower.username for follower in followers.values()]
    return follower_usernames


def get_post_likers(client: Client, post_url: str) -> list:
    """
    Get a list of usernames who liked the post at `post_url`.

    Parameters
    ----------
    client : instagrapi.Client
    post_url : str, https://www.instagram.com/p/<post-id>/

    Returns
    -------
    liker_usernames : list of strings, one per liker
    """

    logging.info(f"Getting {post_url} likers")

    post_id = client.media_pk_from_url(post_url)
    likers = client.media_likers(post_id)
    liker_usernames = [liker.username for liker in likers]

    logging.info(f"Found {len(liker_usernames)} likers")

    return liker_usernames


def get_post_commenters(client: Client, post_url: str) -> list:
    """
    Get a list of usernames who commented on the post at `post_url`.
    Excludes comments from the user associated with `client`.

    Parameters
    ----------
    client : instagrapi.Client
    post_url : str, https://www.instagram.com/p/<post-id>/

    Returns
    -------
    commenter_usernames : list of strings, one per commenter
    """

    logging.info(f"Getting {post_url} commenters")

    post_id = client.media_pk_from_url(post_url)  # TODO grab post_id in main()
    commenters = client.media_comments(post_id)
    commenter_usernames = [
        commenter.user.username for commenter in commenters
        if commenter.user.username != client.username
    ]

    logging.info(f"Found {len(commenter_usernames)} commenters")

    return commenter_usernames


def get_post_datetime(client: Client, post_url: str) -> datetime:
    """
    Get the time at which `post_url` was posted.

    Parameters
    ----------
    client : instagrapi.Client
    post_url : str, https://www.instagram.com/p/<post-id>/

    Returns
    -------
    post_info.taken_at : datetime (UTC)
    """

    post_id = client.media_pk_from_url(post_url)
    post_info = client.media_info(post_id)
    return post_info.taken_at


def get_mentioners(client: Client, usernames: list, start_time: str,
                   thread_limit: int = 5000) -> list:
    """
    Get a list of users who have mentioned the running user in their stories at
    some point after `start_time`.

    This method is inefficient and imprecise. I am not aware of a way to
    explicity grab a list of users who have shared a given post, or even a list
    of users who have mentioned the running user in their stories.

    As a workaround, this function grabs all direct message threads (up to
    `thread_limit`), and filters to the following in this order:
        - DMs from users in `usernames` (typically a list of followers)
        - DMs after the start_time (typically the time of the giveaway post)
        - DMs mentioning the running user
            - These messages have `reel_share` info, with type "mention",
              and the `mentioned_user_id` is the running user

    Note: This requires that users mention your account. Post shares without a
    mention will not be captured. This may capture mentions that are not
    associated with a share (e.g. a user mentions you in their story in some
    unrelated context).

    Parameters
    ----------
    client : instagrapi.Client
    usernames : list of usernames for which DMs should be checked
    start_time : datetime, DMs before this point will not be checked
    thread_limit : maximum number of DM threads to pull

    Returns
    -------
    mentioner_usernames : list of strings, one per mentioners
    """

    logging.info("Getting story mentioners")

    mentioner_usernames = []

    threads = client.direct_threads(amount = thread_limit)

    # possibly a bug: if you tag multiple users in a story it shows up as one
    # "thread" with no users. exclude those here - any individual threads with
    # those users will remain
    threads = [t for t in threads if t.users]

    relevant_threads = [t for t in threads if t.users[0].username in usernames]

    for thread in relevant_threads:
        messages = thread.messages
        messages_after_post = [m for m in messages if m.timestamp > start_time]
        mentions_or_reactions = [m for m in messages if m.reel_share]
        mentions = [m.reel_share for m in mentions_or_reactions if m.reel_share["type"] == "mention"]
        mentions_user = [m for m in mentions if m["mentioned_user_id"] == client.user_id]

        if mentions_user:
            mentioner_usernames.append(thread.users[0].username)

    logging.info(f"Found {len(mentioner_usernames)} mentioners")

    return mentioner_usernames


def create_giveaway_list(followers: list, likers: list,
                         commenters: list, mentioners: list) -> list:
    """
    Create the final giveaway list. Begin with those who follow and liked the
    post. Additional entries for comments and mentions. Usernames can be
    duplicated in the returned list if they also commented and/or mentioned.

    Parameters
    ----------
    followers : list of usernames
    likers : list of usernames
    commenters : list of usernames
    mentioners : list of usernames

    Returns
    -------
    list of usernames (1 per entry)
    """

    followed_and_liked = set(followers).intersection(set(likers))
    commented = set(commenters).intersection(followed_and_liked)
    mentioned = set(mentioners).intersection(followed_and_liked)

    logging.info(f"""
        {len(followed_and_liked)} followers liked
        {len(commented)} followers liked and commented
        {len(mentioned)} followers liked and mentioned
    """)

    return list(followed_and_liked) + list(commented) + list(mentioned)


def main(username: str, post_url: str, client: Client = None,
         twofactor: bool = True, refresh_login: bool = False):

    client = client or get_client()

    maybe_login(client, username, twofactor, refresh_login)

    followers = get_follower_list(client)
    likers = get_post_likers(client, post_url)
    commenters = get_post_commenters(client, post_url)

    post_datetime = get_post_datetime(client, post_url)
    mentioners = get_mentioners(client, set(followers).intersection(set(likers)), post_datetime)

    full_list = create_giveaway_list(followers, likers, commenters, mentioners)

    logging.info(f"Selecting a winner from {len(full_list)} entries")

    winner = random.choice(full_list)

    return {
        "followers": followers,
        "likers": likers,
        "commenters": commenters,
        "mentioners": mentioners,
        "winner": winner
    }
