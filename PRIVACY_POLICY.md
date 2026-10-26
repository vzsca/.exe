# .exe Privacy Policy Template

Last updated: October 26, 2026

## 1. Scope and controller

.exe is open-source software run on the infrastructure of whoever installs it. The data controller therefore depends on the operator of each instance. This document describes the behavior intended by this repository; operators must verify it against the exact version and configuration they deploy.

## 2. Data the software may process

Depending on the commands and scripts used, the bot may process:
- Discord user IDs for command authors and moderation targets;
- server, channel, and role IDs needed to execute commands;
- command and script content, including replies submitted to .exe input declarations;
- named scripts saved by users, associated with their Discord user ID;
- user IDs stored in the execution whitelist;
- technical information and errors written to application logs.

Saved scripts and whitelist entries are stored in the operator-configured SQLite database. Logs may include execution metadata and IDs. Operators should inspect the code and configuration of their deployed version to confirm exactly what is retained.

## 3. Purposes and legal basis

This data is used to execute commands, enforce access control, save requested scripts, manage the whitelist, diagnose errors, and protect the bot against unauthorized use. Where an instance is subject to GDPR, the operator must determine and document the applicable legal basis.

## 4. Recipients and third-party services

Commands are handled by the bot hosted by the operator and sent to Discord through its API. Discord processes data under its own terms and privacy policy. Access to the SQLite database and logs should be limited to the operator and authorized people.

## 5. Retention and security

Retention periods depend on the operator's configuration and practices. Scripts and whitelist entries can be deleted using available features or directly from the database. Protect the SQLite file, logs, backups, and .env file. Never publish the bot token, and do not store sensitive data in scripts or their inputs.

## 6. Rights and contact

Requests to access, correct, or delete data should be sent to the operator of the relevant instance, who must respond under applicable law. For issues or corrections related to the software repository, use https://github.com/vzsca/.exe/issues.

## 7. Limitations

This policy is a starting template and does not by itself guarantee GDPR compliance. Before deploying the bot, operators should confirm actual processing, add their contact details, define retention periods, disclose any transfers, and explain how data-subject rights can be exercised.
