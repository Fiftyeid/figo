# figo

## Weekly Facebook Page scheduler

`scripts/fb_schedule.py` schedules one photo post per row of a CSV plan through the Meta Graph API. Posts are created as scheduled posts on the Page, so Meta publishes them at the set times.

### 1. Get a Page access token

1. Create an app at https://developers.facebook.com and add the Facebook Login / Pages API products.
2. Give it the `pages_manage_posts` and `pages_read_engagement` permissions. Your Page admin must approve them, and the app must be in a state that allows your account to use them.
3. Generate a **Page access token** for page `61570668525616` (the Page ID is `61570668525616`).

Keep the token out of the repo. Pass it as an environment variable.

### 2. Prepare the content

- Put images in `content/images/` (`day1.jpg` ... `day7.jpg`).
- Edit `content/week_plan.csv`: captions, and `publish_at` times with a UTC offset.

### 3. Run

```bash
export FB_PAGE_ID=61570668525616
export FB_PAGE_TOKEN=...your token...

# Dry run: validates the CSV, image files and publish times. Changes nothing.
python3 scripts/fb_schedule.py content/week_plan.csv

# Schedule for real
python3 scripts/fb_schedule.py content/week_plan.csv --execute
```

Check the result in Meta Business Suite under Posts, then Scheduled.

### Notes

- Scheduled times must be at least 10 minutes ahead and within Meta's allowed window. Check the current limit in Meta's docs.
- The script only schedules original posts you provide. Don't use it to buy followers, add fake engagement, or post the same content repeatedly to game reach. That breaks Meta's rules and can cost the Page its monetization.
