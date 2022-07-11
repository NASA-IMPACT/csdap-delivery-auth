# Cognito Access Script

## Set up

1. Install this tool: `pip install git+https://github.com/NASA-IMPACT/csdap-delivery-auth.git`
2. Configure required environment variables by following `.env.template`

## Use with AWS CLI

1. Create a script to call the credential retrieval script. This is necessary because AWS' `credential_process` option is limited in how it calls external processes. Save the script and name it `getcreds.sh`

```
#!/bin/bash
export TOTP_TOKEN=<MFA Secret Code>
csdap-auth get-credentials -u $1 -p $2 --mfa-code=$(totp-cli instant)
```

2. Edit `~/.aws/credentials` and add a new profile:

```
...

[csdap]
credential_process = "/absolute/path/to/getcreds.sh"
```

3. Run your data delivery script with this AWS profile selected:

```
$ AWS_PROFILE=csdap data_delivery.sh
```

## TODO

- [] Add command for setting up a new account
