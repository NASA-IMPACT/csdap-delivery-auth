from botocore.config import Config
from botocore import UNSIGNED
import boto3
import click
import json
from typing import Optional
import sys

from csdap_delivery_auth.exceptions import InvalidPassword


@click.group()
def cli():
    pass


def initiate_auth(idp_client, username: str, password: str, cognito_client_id: str):
    try:
        return idp_client.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
            },
            ClientId=cognito_client_id,
        )
    except idp_client.exceptions.NotAuthorizedException:
        raise InvalidPassword


def mfa_auth(
    idp_client,
    username: str,
    challenge_name: str,
    session: str,
    cognito_client_id: str,
    mfa_code: Optional[str],
) -> dict:
    mfa_code = mfa_code or input("Enter MFA code: ")
    mfa_response = idp_client.respond_to_auth_challenge(
        ChallengeName=challenge_name,
        ChallengeResponses={
            "USERNAME": username,
            f"{challenge_name}_CODE": mfa_code,
        },
        ClientId=cognito_client_id,
        Session=session,
    )
    return mfa_response["AuthenticationResult"]


def mfa_setup_workflow(
    idp_client, access_token: Optional[str] = None, session: Optional[str] = None
):
    associate_kwargs = {}
    if access_token:
        associate_kwargs = {"AccessToken": access_token}
    elif session:
        associate_kwargs = {"Session": session}
    associate_response = idp_client.associate_software_token(**associate_kwargs)

    if associate_response.get("Session"):
        associate_kwargs = {"Session": associate_response["Session"]}

    click.echo(
        "Add the following secret code to your authentication"
        f" app:\n{associate_response['SecretCode']}"
    )
    otp = input("Generate a code with your authentication app and enter it here: ")

    verify_response = idp_client.verify_software_token(UserCode=otp, **associate_kwargs)

    if verify_response["Status"] == "SUCCESS":
        click.echo("MFA authentication added to your account.")
    else:
        click.echo("Something went wrong adding MFA Authentication to your account.")


@cli.command()
@click.option("-u", "--username", prompt=True)
@click.option("-p", "--password", prompt=True, hide_input=True)
@click.option("--aws-region", envvar="AWS_REGION", show_envvar=True)
@click.option("--cognito-client-id", envvar="COGNITO_CLIENT_ID", show_envvar=True)
def setup_account(
    username: str,
    password: str,
    aws_region: str,
    cognito_client_id: str,
):
    idp_client = boto3.client(
        "cognito-idp", region_name=aws_region, config=Config(signature_version=UNSIGNED)
    )
    try:
        response = initiate_auth(idp_client, username, password, cognito_client_id)
    except InvalidPassword:
        click.echo("Invalid username or password")
        sys.exit(-1)

    session = response["Session"]

    if response.get("ChallengeName") == "NEW_PASSWORD_REQUIRED":
        required_attribute_keys = json.loads(
            response["ChallengeParameters"].get("requiredAttributes", "[]")
        )
        password_set = False
        while not password_set:
            new_password = input("Enter new password: ")
            required_attribute_values = {}
            for attribute in required_attribute_keys:
                required_attribute_values[attribute] = input(
                    f"Enter a value for {attribute}: "
                )
            try:
                password_response = idp_client.respond_to_auth_challenge(
                    ChallengeName=response["ChallengeName"],
                    ChallengeResponses={
                        "USERNAME": username,
                        "NEW_PASSWORD": new_password,
                        **required_attribute_values,
                    },
                    ClientId=cognito_client_id,
                    Session=session,
                )
            except idp_client.exceptions.InvalidPasswordException as err:
                click.echo(err)
            else:
                password_set = True
                click.echo("New password set")
                if password_response.get("ChallengeName") == "MFA_SETUP":
                    mfa_setup_workflow(
                        idp_client=idp_client,
                        session=password_response["Session"],
                    )
    else:
        click.echo("Password already set up")
        sys.exit(-1)


@cli.command()
@click.option("-u", "--username", prompt=True)
@click.option("--aws-region", envvar="AWS_REGION", show_envvar=True)
@click.option("--cognito-client-id", envvar="COGNITO_CLIENT_ID", show_envvar=True)
def reset_password(
    username: str,
    aws_region: str,
    cognito_client_id: str,
):
    idp_client = boto3.client(
        "cognito-idp", region_name=aws_region, config=Config(signature_version=UNSIGNED)
    )
    response = idp_client.forgot_password(Username=username, ClientId=cognito_client_id)

    delivery_medium = response["CodeDeliveryDetails"]["DeliveryMedium"]
    click.echo(
        f"Reset password code delivered by {delivery_medium}. Please retrieve it and"
        " enter it here."
    )

    reset_code = input("Reset Password Code: ")

    new_password_set = False
    while not new_password_set:
        new_password = input("Enter New Password: ")
        try:
            idp_client.confirm_forgot_password(
                ClientId=cognito_client_id,
                ConfirmationCode=reset_code,
                Password=new_password,
                Username=username,
            )
        except idp_client.exceptions.InvalidPasswordException as err:
            click.echo(err)
        else:
            new_password_set = True
    click.echo("New Password Set")


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
    try:
        response = initiate_auth(idp_client, username, password, cognito_client_id)
    except InvalidPassword:
        click.echo("Invalid username or password")
        sys.exit(-1)

    if response.get("ChallengeName") in ("SOFTWARE_TOKEN_MFA", "SMS_MFA"):
        session = response["Session"]
        auth_result = mfa_auth(
            idp_client,
            username,
            response["ChallengeName"],
            session,
            cognito_client_id,
            mfa_code,
        )
    elif response.get("ChallengeName") == "MFA_SETUP":
        mfa_setup_workflow(idp_client, session=response["Session"])
        return
    else:
        auth_result = response["AuthenticationResult"]

    mfa_setup_workflow(idp_client, access_token=auth_result["AccessToken"])


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
        response = initiate_auth(idp_client, username, password, cognito_client_id)
    except InvalidPassword:
        click.echo("Invalid username or password")
        sys.exit(-1)

    if response.get("ChallengeName") in ("SOFTWARE_TOKEN_MFA", "SMS_MFA"):
        auth_result = mfa_auth(
            idp_client,
            username,
            response["ChallengeName"],
            response["Session"],
            cognito_client_id,
            mfa_code,
        )
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
                f"cognito-idp.{aws_region}.amazonaws.com/{cognito_user_pool_id}": id_token  # noqa:E501
            },
        )
    except Exception as err:  # noqa:E722
        click.echo(err)
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
                f"cognito-idp.{aws_region}.amazonaws.com/{cognito_user_pool_id}": id_token  # noqa:E501
            },
        )
    except Exception as err:  # noqa:E722
        click.echo(err)
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


@cli.command()
def version():
    import pkg_resources  # part of setuptools

    version = pkg_resources.require("csdap_delivery_auth")[0].version
    click.echo(version)


if __name__ == "__main__":
    get_credentials()
