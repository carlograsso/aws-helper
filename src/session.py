import requests
import boto3
import json
import urllib.parse
import os
import sys
import utils

HOME=os.getenv("HOME")
CONFIGPATH=f'{HOME}/.aws/config'
CREDSPATH=f'{HOME}/.aws/credentials'


class SessionHelper:
    def __init__(self, toFind, region, configPath, credsPath):
        self.toFind = toFind
        self.region = region
        self.configPath = configPath
        self.credsPath = credsPath
        self.profiles = None
        self.users = None
        self.entity = None
        self.tempCreds = None

    def start(self):
        self.profileScanner()
        self.userScanner()
        
   
        self.entity_lister()
        if len(self.profiles) + len(self.users) > 1:
            print("Select one Entity: ")
            choice = utils.choiceEvaluator([len(self.profiles)+len(self.users)])
        else:
            choice = 1
        self.entity=(self.profiles+self.users)[int(choice) -1]

        if self.entity["type"] == "profile":
            creds=self.assumeRole()
            self.openConsole()
        elif self.entity["type"] == "user":
            creds=self.getSessionToken()
            self.openConsole()
        return
    

    def profileScanner(self):
        self.profiles=[]
        profile=-1
        new_profile=-1
        with open(self.configPath, 'r') as file:
            lines = file.readlines()
            for index, line in enumerate(lines):
                if line.find("[profile") != -1 and line.find(self.toFind) == -1:
                    new_profile=-1
                    if profile != -1:
                        self.profiles.append(profile) 
                    profile=-1
                elif line.find("[profile") != -1 and line.find(self.toFind) != -1:
                    new_profile=1
                    if profile != -1:
                        self.profiles.append(profile)                
                    profile = { "name": line.split("[profile ")[-1][:-2],
                                "type": "profile" }
                    if profile["name"] == self.toFind:
                        profile["exact_match"] = True
                    else:
                        profile["exact_match"] = False            
                elif line.find("role_arn") != -1 and new_profile == 1:
                    profile["role_arn"] = line.split("=")[1].strip()
                elif line.find("source_profile") != -1 and new_profile == 1:
                    profile["source_profile"] = line.split("=")[1].strip()
                elif line.find("region") != -1 and new_profile == 1:
                    profile["region"] = line.split("=")[1].strip()
                
                if index == len(lines) -1 and profile != -1:
                    self.profiles.append(profile)
        return

    def userScanner(self):
        self.users=[]
        user=-1
        new_user=-1
        with open(self.credsPath, 'r') as file:
            lines = file.readlines()
            for index, line in enumerate(lines):
                if line[0] == "[" and line.find(self.toFind) == -1:
                    new_user=-1
                    if user != -1:
                        self.users.append(user) 
                    user=-1
                elif line.find("[") != -1 and line.find(self.toFind) != -1:
                    new_user=1
                    if user != -1:
                        self.users.append(user)                
                    user = { "name": line.split("[")[-1][:-2],
                            "type": "user" }
                    if user["name"] == self.toFind:
                        user["exact_match"] = True
                    else:
                        user["exact_match"] = False            
                elif line.find("aws_access_key_id") != -1 and new_user == 1:
                    user["aws_access_key_id"] = line.split("=")[1].strip()
                elif line.find("aws_secre_access_key") != -1 and new_user == 1:
                    user["aws_secre_access_key"] = line.split("=")[1].strip()
                elif line.find("region") != -1 and new_user == 1:
                    user["region"] = line.split("=")[1].strip()
                
                if index == len(lines) -1 and user != -1:
                    self.users.append(user)
        return
    
    def entity_lister(self):
        if len(self.profiles) != 0: 
            print("Profiles Found:")
            for index, value in enumerate(self.profiles):
                print(f"{index + 1} - {value['name']}")
        if len(self.users) != 0: 
            print("Users Found:")
            for index, value in enumerate(self.users):
                print(f"{len(self.profiles) + index + 1 if self.profiles else 1 + index} - {value['name']}")
        return
    
    def assumeRole(self):
        session = boto3.Session(profile_name=self.entity["source_profile"])
        sts = session.client("sts")
        response = sts.assume_role(
            RoleArn=self.entity["role_arn"],
            RoleSessionName=f"{self.entity['name']}-fromCli"
        )
        self.tempCreds={"name": self.entity["name"], "AccessKeyId": response["Credentials"]["AccessKeyId"], "SecretAccessKey": response["Credentials"]["SecretAccessKey"], "SessionToken": response["Credentials"]["SessionToken"]}
        return
    
    def getSessionToken(self):
        session = boto3.Session(profile_name=self.entity["name"])
        sts = session.client("sts")
        response= sts.get_session_token()
        self.tempCreds={"name": self.entity["name"], "AccessKeyId": response["Credentials"]["AccessKeyId"], "SecretAccessKey": response["Credentials"]["SecretAccessKey"], "SessionToken": response["Credentials"]["SessionToken"]}
        return
    
    def openConsole(self):
        baseUrl = 'https://signin.aws.amazon.com/federation'
        cred_json ={"sessionId": self.tempCreds["AccessKeyId"], "sessionKey": self.tempCreds["SecretAccessKey"], "sessionToken": self.tempCreds["SessionToken"]}
        formatted_creds = json.dumps(cred_json)
        encoded=urllib.parse.quote(formatted_creds)
        
        response = requests.get( baseUrl + '?Action=getSigninToken&Session=' + encoded)

        destination = 'https://console.aws.amazon.com/'
        encoded_destination=urllib.parse.quote(destination)
        response_load = json.loads(response.content)


        econded_token = urllib.parse.quote(response_load["SigninToken"])
        url = baseUrl + '?Action=login&Destination=' + encoded_destination + '&SigninToken=' + econded_token 

        encoded_url = urllib.parse.quote(url)

        #command=f'/Applications/Firefox.app/Contents/MacOS/firefox "ext+container:name={account}&url={encoded_url}"' 
        command=f'/Applications/LibreWolf.app/Contents/MacOS/librewolf "ext+container:name={self.entity["name"]}&url={encoded_url}"'

        print(f"Opening console for {self.entity['name']}")
        os.system(command)
        return

