# CSDAP Delivery Auth Script

## Installation and Configuration

1. You will receive an email with your username and temporary password. Separately, you will receive configuration details for your environment.
1. Install this tool: `pip3 install --user https://github.com/NASA-IMPACT/csdap-delivery-auth/archive/main.zip`
1. Copy `.env.template` into a new file called `.env` and populate it with the configuration provided to you in Step #1.

## Set up your account

1. Load the environment variables you configured in the previous step: `source .env`
1. Make note of the username and password you received by email. Run the account setup command: `csdap-auth setup-account -u <username> -p "<temporary password>"`
1. Create a new password and provide it when prompted. Provide your name as well, when prompted.

## Set up Multi Factor Authentication (MFA)

1. Install and configure a tool for generating Time-based One Time Passwords (TOTP) on the command line, such as https://github.com/yitsushi/totp-cli.
2. Set up MFA on your account: `csdap-auth setup-mfa -u <username> -p "<password>"`
3. A secret code will be displayed. Either add this code to your TOTP tool or store it somewhere secure if you will be generating TOTP codes adhoc (e.g. with `totp-cli instant`).
4. Generate a TOTP code using the provided secret and enter it when prompted to finish setting up MFA on your account.

## Test getting credentials

1. Run `csdap-auth get-credentials -u <username> -p "<password>" --mfa-code=<mfa code>`
2. If everything is configured correctly, you should receive a JSON document with Access Keys and a Session Token.

## Automatically get credentials for your AWS Profile

1. You can configure your AWS profile to automatically generate temporary credentials for your account.
2. First, create a script using the template below to call the credential retrieval script. This is necessary because AWS' `credential_process` option is limited in how it calls external processes. Save the script and name it `getcreds.sh`. If you are using an MFA tool other than `totp-cli`, replace that part of the template (and the TOTP_TOKEN line) with the appropriate command for generating a TOTP code. Note that the command run by `credential_process` is **not interactive**, so you must provide all necessary inputs either in the script or in environment variables.

```
#!/bin/bash
export TOTP_TOKEN=<MFA Secret Code>
csdap-auth get-credentials -u $1 -p $2 --mfa-code=$(totp-cli instant)
```

3. Edit `~/.aws/credentials` and add a new profile, replacing `/absolute/path/to/getcreds.sh` with the actual absolute path to that script:

```
...

[csdap]
credential_process = "/absolute/path/to/getcreds.sh" <username> "<password>"
```

4. Test that you have access to the desired S3 bucket:

```
$ echo "something" > testfile
$ AWS_PROFILE=csdap aws s3 cp testfile s3://<bucket>/testfile
```

5. When you run your data delivery script, ensure the correct AWS profile is selected:

```
$ AWS_PROFILE=csdap your_data_delivery_script.sh
```
