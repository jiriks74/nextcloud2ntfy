# nextcloud-ntfy.sh

Are you tired of Nextcloud
[**still not supporting notifications F-Droid**](https://github.com/nextcloud/talk-android/issues/257)?
After 4 years I sure am!

But you don't have to be because I solved it for you! Simply run this brigde,
install install the `ntfy` app and you're done!

## Features

- 💻 Can be run on any machine with Python 3
- 🌐 Support for both the official `ntfy.sh` and self-hosted instances
- 🔒 Support for token authentication with `ntfy`
- 🗑️ Dismiss button to remove the notification on Nextcloud too
- 🛠️ Action buttons*

> [!Note]
> \* Action buttons currently open the browser instead of launching the correct
>    app. I haven't found any mention of Nextcloud supporting app URLs (eg. `twitter://`)

## Setup

### 0. Create a new application password for your Nextcloud account

This is better as if you leak you can easily remove it and no other passwords
can be guessed from it.

> [!Note]
> If your passwords can be guessed from knowing other passwords consider
> using a password manager and generated passwords...

### 1. On the machine running the bridge

1. Grab a release
2. Create a config file: `cp config-example.json config.json`
3. Fill out the necessary values, they should be self-explanatory:
  - `ntfy_topic`
  - `nextcloud_base_url`
  - `nextcloud_username`
  - `nextcloud_password`
4. Start the bridge: `python3 main.py -c config.json`

> [!CAUTION]
> On `ntfy.sh` (and instances with `auth-default-access` set to `read-write`)
> you **need** to set a secure topic id. It acts as your password so
> **if anyone gets your topic id they can read all your notifications!**

### 2. On your phone

1. Install [the `ntfy.sh` app](https://f-droid.org/en/packages/io.heckel.ntfy/)
2. Click the `+` button in the bottom right corner
3. Input the topic you set in `config.json`

### 3. Profit

## How did this happen?

I wanted to self-host `ntfy` so that I'd get better UnifiedPush experience
than I had with the [Nextcloud UnifiedPush Provider](https://apps.nextcloud.com/apps/uppush)
app. My Nextcloud instance shuts down for backups (generates a notification error in the app)
and you have to set up redirects in order to get Matrix notifications working.

So I got `ntfy` working and I saw that the documentation has
[Integrations + community projects](https://docs.ntfy.sh/integrations/)
section.

Going through it I found this video: https://www.youtube.com/watch?v=0a6PpfN5PD8

It's about a script someone created to pull notifications from Nextcloud and
push them to `ntfy`. I found it interesting but from a quick look at the script
it was more limited than I'd like it to be. for example the notifications
were immediately removed from Nextcloud which I didn't like.

As the script didn't have any license attached I decided to make my own
from the ground up. Within 90 minutes I had a working prototype sending
notifications to my phone.

From there I continued my work. First I created the `Dismiss` button.
Then I noticed that `ntfy` can create action buttons so
I parsed Nextcloud's notification buttons into something `ntfy` can understand. 

In about 4-5 hour I had basically all the features finished. Hopefully I'll
be able to add more (like opening the Nextcloud App instead of the browser)
but we'll see what's possible.
