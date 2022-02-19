# alexander

alexander is a simple yet effective way to create a Telegram inline Bot for audio files.

# How to use alexander

Download the source code using the following command: 

`$ git clone https://github.com/davleone/alexander`

Then install required dependencies:

`$ pip install -r requirements.txt`

Comments in **config.yaml** explain each setting and how editing them impacts the activity of the software. Feel free to edit the configuration file according to your needs. 

Contact [@BotFather](https://t.me/botfather) to get your Bot token, enable inline queries and (optionally) enable inline feedback. 

You can then run the software with the following command:

`$ python main.py`

In some cases (e.g. Linux cronjob) you might find useful to specify the absolute path of the config.yaml file in main.py; you can easily do so by modifying the corresponding strings.

## How it works

By using this software you can operate a Telegram inline Bot that provides a list of audio files in response to an inline query. An example of an inline Telegram Bot (in this case, for GIFs) is @gif.

Any Telegram user can pass an inline query just typing *"@username query"* in any chat.

This software is able to: 
- provide to any user a sorted list of relevant audio files for the query received; 
- add/remove audio files, directly in the private chat with any admin; 
- set/remove a description against which queries will be compared for any audio, directly in the private chat with any admin;
- keep track of the number of "views" each audio has received. 

You can change the way a query is answered, add a custom caption to every audio, and many other things in the config.yaml file.  

# Contributing 

This software was developed for my personal use, so if you have specific needs, radically different goals, etc. you should probably fork this repo. 

You can help by: 
- **providing bug reports** (with as much information as possible, such as your CONFIG.yaml and your log files);
- **share your ideas** on how to improve the software;
- **updating and correcting** the documentation;
- **sending a pull request**.
- 
## Versioning conventions

We follow a simple _Major.Minor.Patch_ convention.

A major release is one that changes the config.yaml file.
A minor release is one that adds new features to the software without changing the config.yaml file.
A patch release is one that does nor adds new features nor changes the config.yaml file.
