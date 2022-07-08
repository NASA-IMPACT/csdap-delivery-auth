from botocore.config import Config
from botocore import UNSIGNED
import boto3
import click
import json
from typing import Optional
import sys


@click.group()
def cli():
    pass


@cli.command()
@click.option("-u", "--username", prompt=True)
@click.option("-p", "--password", prompt=True, hide_input=True)
@click.option("--aws-region", envvar="AWS_REGION", show_envvar=True)
@click.option("--cognito-client-id", envvar="COGNITO_CLIENT_ID", show_envvar=True)
@click.option("--current-mfa-code", "mfa_code", default=None, required=False)
def setup_mfa(
    username: str,
    password: str,
    aws_region: str,
    cognito_client_id: str,
    mfa_code: Optional[str],
):
    idp_client = boto3.client(
        "cognito-idp", region_name=aws_region, config=Config(signature_version=UNSIGNED)
    )
    response = idp_client.initiate_auth(
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": username,
            "PASSWORD": password,
        },
        ClientId=cognito_client_id,
    )
    session = response["Session"]

    if "ChallengeName" in response:
        mfa_code = mfa_code or input("Enter MFA code: ")
        mfa_response = idp_client.respond_to_auth_challenge(
            ChallengeName=response["ChallengeName"],
            ChallengeResponses={
                "USERNAME": username,
                f"{response['ChallengeName']}_CODE": mfa_code,
            },
            ClientId=cognito_client_id,
            Session=session,
        )
        auth_result = mfa_response["AuthenticationResult"]
    else:
        auth_result = response["AuthenticationResult"]

    associate_response = idp_client.associate_software_token(
        AccessToken=auth_result["AccessToken"]
    )
    click.echo(associate_response)
    click.echo(
        f"Add the following secret code to your authentication app:\n{associate_response['SecretCode']}"
    )
    otp = input("Generate a code with your authentication app and enter it here: ")

    verify_response = idp_client.verify_software_token(
        AccessToken=auth_result["AccessToken"], UserCode=otp
    )

    if verify_response["Status"] == "SUCCESS":
        click.echo("Success! MFA authentication added to your account.")
    else:
        click.echo("Failed! Something went wrong.")


@cli.command()
@click.option("-u", "--username", prompt=True)
@click.option("-p", "--password", prompt=True, hide_input=True)
@click.option("--aws-account-id", envvar="AWS_ACCOUNT_ID", show_envvar=True)
@click.option("--aws-region", envvar="AWS_REGION", show_envvar=True)
@click.option(
    "--cognito-identity-pool-id", envvar="COGNITO_IDENTITY_POOL_ID", show_envvar=True
)
@click.option("--cognito-user-pool-id", envvar="COGNITO_USER_POOL_ID", show_envvar=True)
@click.option("--cognito-client-id", envvar="COGNITO_CLIENT_ID", show_envvar=True)
@click.option("--mfa-code", default=None, required=False)
def get_credentials(
    username: str,
    password: str,
    aws_account_id: str,
    aws_region: str,
    cognito_identity_pool_id: str,
    cognito_user_pool_id: str,
    cognito_client_id: str,
    mfa_code: Optional[str],
):
    idp_client = boto3.client(
        "cognito-idp", region_name=aws_region, config=Config(signature_version=UNSIGNED)
    )
    identity_client = boto3.client(
        "cognito-identity",
        region_name=aws_region,
        config=Config(signature_version=UNSIGNED),
    )
    try:
        response = idp_client.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
            },
            ClientId=cognito_client_id,
        )
    except:
        sys.exit(-1)

    if "ChallengeName" in response:
        mfa_code = mfa_code or input("Enter MFA code: ")
        mfa_response = idp_client.respond_to_auth_challenge(
            ChallengeName=response["ChallengeName"],
            ChallengeResponses={
                "USERNAME": username,
                f"{response['ChallengeName']}_CODE": mfa_code,
            },
            ClientId=cognito_client_id,
            Session=response["Session"],
        )
        auth_result = mfa_response["AuthenticationResult"]
    else:
        auth_result = response["AuthenticationResult"]

    try:
        id_token = auth_result["IdToken"]
    except KeyError:
        click.echo(response)
        sys.exit(-1)

    try:
        id_response = identity_client.get_id(
            AccountId=aws_account_id,
            IdentityPoolId=cognito_identity_pool_id,
            Logins={
                f"cognito-idp.{aws_region}.amazonaws.com/{cognito_user_pool_id}": id_token
            },
        )
    except:
        sys.exit(-1)

    try:
        identity_id = id_response["IdentityId"]
    except KeyError:
        click.echo(id_response)
        sys.exit(-1)

    try:
        credentials_response = identity_client.get_credentials_for_identity(
            IdentityId=identity_id,
            Logins={
                f"cognito-idp.{aws_region}.amazonaws.com/{cognito_user_pool_id}": id_token
            },
        )
    except:
        sys.exit(-1)

    click.echo(
        json.dumps(
            {
                "Version": 1,
                "AccessKeyId": credentials_response["Credentials"]["AccessKeyId"],
                "SecretAccessKey": credentials_response["Credentials"]["SecretKey"],
                "SessionToken": credentials_response["Credentials"]["SessionToken"],
                "Expiration": credentials_response["Credentials"][
                    "Expiration"
                ].isoformat(),
            }
        )
    )


if __name__ == "__main__":
    get_credentials()
