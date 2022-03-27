# Instagram Insights

I run an instagram account for eye makeup ([@emmas__eye](https://www.instagram.com/emmas__eye/?hl=en)) and occasionally have the opportunity to work with brands. Sharing my account insights helps to justify my rates. However, it's not that easy to calculate insights in the app – for the most accurate measurement, you have to check the insights for each post individually and then do your own calculations.

This script uses [instagrapi](https://adw0rd.github.io/instagrapi/) to pull insights for your recent posts (20 posts by default). It then calculates reach per post, impressions per post, shares per post, and engagement. Engagement here is defined as `(likes per post + comments per post) / current follower count`.

You must have a ["Professional"](https://sproutsocial.com/insights/instagram-business-profile/) Instagram account in order for Insights to be accessible.

### Usage
```{python}
run instagram_insights.py

# Instantiate the instagrapi client once with get_client()
# and re-use that with get_account_performance()
# to avoid needing to login on every run.

client = get_client()

insights = get_account_performance(
  username="emmas__eye",
  client=client
)
```

#### Login information
On the first run, `get_account_performance()` will request your Instagram password and (if `twofactor`) a 2FA `verification_code`. On subsequent runs, it will skip login if you pass in the same `client` object. If you don't pass in the same `client` object, it will use the `IG_PASSWORD_<username>` environment variable that was stored during the previous run. It will still request a 2FA `verification_code` if applicable.

On each login, it is likely that Instagram will send a notification about an "unrecognized" login. It's a good idea to click through to that notification and select "This Was Me" so that Instagram knows it was an authorized login.

#### Example output

```
{
  'current_follower_count': 9611,
  'engagement': 0.30970242430548334,
  'per_post_impressions': 32398.5,
  'per_post_reach': 31125.15,
  'per_post_shares': 127.55,
  'posts': 20
}
 ```


 ### To Do
* Generate a nicely formatted report using the output above.
* Expand to a more comprehensive `influencer` package. Ideas:
  * Invoice creation and tracking
  * Hashtag exploration - charting reach for each hashtag used
  * Insights over time – charts, etc.
  * Giveaway helpers – pull list of followers, select one at random, etc.
