from instagrapi import Client
from getpass import getpass
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
