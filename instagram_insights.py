from instagrapi.types import Media
from instagrapi import Client
from getpass import getpass
import pandas as pd
import logging
import os


logging.getLogger().setLevel(logging.INFO)


def get_client() -> Client:
    """
    Instantiate an instagrapi.Client. Useful to run independently and pass
    to get_account_performance() to avoid having to re-login on each run.

    Returns
    -------
    instagrapi.Client
    """
    return Client()


def check_login_status(client: Client) -> bool:
    """
    Check whether we're already logged in. No need to login again if so.

    Parameters
    ----------
    client : instagrapi.Client

    Returns
    -------
    True if logged in.
    """

    logging.info("Checking login status.")

    try:
        # relatively quick call that requires login
        account_insights = client.insights_account()
        return True
    except AssertionError as e:
        if str(e) == "Login required":
            return False


def maybe_login(client: Client, username: str,
                twofactor: bool = True, refresh_login: bool = False) -> None:
    """
    Login if we're not already logged in. If password is stored from previous
    session, use that. Otherwise, request input. Request 2FA verification code
    if 2FA enabled.

    Parameters
    ----------
    client : instagrapi.Client
    username : str, Instagram username
    twofactor : bool, optional
        True if 2FA enabled (default True)
    refresh_login : bool, optional
        True to force refresh even if already logged in (default False)

    Returns
    -------
    None
    """

    is_logged_in = check_login_status(client)

    if is_logged_in and not refresh_login:
        logging.info("Already logged in.")
        return

    logging.info(f"Logging into {username}.")

    if os.environ.get(f"IG_PASSWORD_{username}"):
        logging.info(f"Using environment variable IG_PASSWORD_{username}.")
        password = os.environ.get(f"IG_PASSWORD_{username}")
    else:
        password = getpass("Password: ")
        os.environ[f"IG_PASSWORD_{username}"] = password

    if twofactor:
        verification_code = getpass("2FA code: ")
    else:
        verification_code = None

    client.login(
        username=username,
        password=password,
        verification_code=verification_code
    )


def get_posts(client: Client, username: str, num_posts: int = 20) -> list:
    """
    Get a list of <num_posts> recent posts, starting with the latest
    and going back in time sequentially.

    Parameters
    ----------
    client : instagrapi.Client
    username : str, Instagram username
    num_posts : int, optional
        number of posts to gather (default 20)

    Returns
    -------
    posts : list of instagrapi.types.Media objects, one per post
    """
    logging.info("Gathering information about each post.")
    user_id = client.user_id_from_username(username)
    posts = client.user_medias(user_id, amount=num_posts)
    return posts


def get_post_insights(client: Client, post: Media) -> pd.DataFrame:
    """
    Pull insights from a post (instagrapi.types.Media) and format
    as a pandas dataframe.

    Parameters
    ----------
    client : instagrapi.Client
    post : instagrapi.types.Media, from get_posts()

    Returns
    -------
    dataframe with reach, impressions, shares, likes, comments, total_engagement
    """
    insights = client.insights_media(post.pk)
    metrics = insights["inline_insights_node"]["metrics"]

    # metrics can be empty for posts prior to becoming a "professional account"
    if not metrics:
        return None

    reach = metrics["reach_count"]
    impressions = metrics["impression_count"]
    shares = sum([x["value"] for x in metrics["share_count"]["tray"]["nodes"]])
    likes = insights["like_count"]
    comments = insights["comment_count"]

    return pd.DataFrame({
        "reach": [reach],
        "impressions": [impressions],
        "shares": [shares],
        "likes": [likes],
        "comments": [comments],
        "total_engagement": [likes + comments]
    }, index=[post.pk])


def calculate_aggregate_insights(insights: pd.DataFrame,
                                 comment_pct: float = 0.5) -> pd.Series:
    """
    Aggregate insights by taking an average over the number of posts analyzed.
    Raw comment count includes responses from the account owner. Those are
    excluded from the count here – default assumption is that account owner
    responds to every comment, so 50% of comments should be dropped.

    Parameters
    ----------
    insights : pd.DataFrame, from get_post_insights()
    comment_pct : float, optional
        percentage of comments responded to by account owner (default 0.5)

    Returns
    -------
    aggs : pd.Series
        average reach, impressions, shares, likes, comments, total_engagement
    """

    logging.info("Aggregating insights.")

    aggs = insights.sum() / len(insights)
    aggs["comments"] = aggs["comments"] * (1 - comment_pct)

    return aggs


def get_account_performance(username: str, client: Client = None,
                            num_posts: int = 20, twofactor: bool = True,
                            refresh_login: bool = False) -> dict:
    """
    Main function to gather account performance data using the functions above.

    Parameters
    ----------
    username : str, Instagram username
    client : instagrapi.Client, optional
        pass in client from previous session to avoid re-logging in
    num_posts : int, optional
        number of posts to gather (default 20)
    twofactor : bool, optional
        True if 2FA enabled (default True)
    refresh_login : bool, optional
        True to force refresh even if already logged in (default False)

    Returns
    -------
    dictionary with posts, current_follower_count, engagement, per_post_reach,
    per_post_impressions, and per_post_shares
    """

    logging.info(
        f"Gathering account performance data from {num_posts} {username} posts."
    )

    client = client or get_client()

    maybe_login(client, username, twofactor, refresh_login)

    posts = get_posts(client, username, num_posts=num_posts)
    insights = [get_post_insights(client, post) for post in posts]

    try:
        insights_df = pd.concat(insights)
    except ValueError:
        logging.info("No insights available.")
        return

    aggregate_insights = calculate_aggregate_insights(insights_df, comment_pct=0.4)

    follower_count = client.user_info_by_username(username).follower_count
    engagement = aggregate_insights["total_engagement"] / follower_count

    return({
        "posts": num_posts,
        "current_follower_count": follower_count,
        "engagement": engagement,
        "per_post_reach": aggregate_insights["reach"],
        "per_post_impressions": aggregate_insights["impressions"],
        "per_post_shares": aggregate_insights["shares"]
    })
