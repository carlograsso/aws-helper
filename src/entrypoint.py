import argparse
import session
from ec2 import Ec2Helper
from session import SessionHelper
import os

HOME=os.getenv("HOME")
CONFIGPATH=f'{HOME}/.aws/config'
CREDSPATH=f'{HOME}/.aws/credentials'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("module", type=str, default=None, help="Module Name (ec2)")
    parser.add_argument("--profile", type=str, default=None, help="aws profile to use")
    parser.add_argument("--region", type=str, default=None, help="aws region to use")
    parser.add_argument('--filters', type=parse_tuple_arg,
                        help='a list of tuples Name:Var, Name:Var')
    parser.add_argument('--configPath', type=str, default=f"{CONFIGPATH}")
    parser.add_argument('--credsPath', type=str, default=CREDSPATH)
    args = parser.parse_args()



    region=args.region
    KeyFolder=f"{os.getenv('HOME')}/.ssh/keys"
    profile=args.profile
    filters=args.filters
    module=args.module 
    configPath=args.configPath if args.configPath else CONFIGPATH
    credsPath=args.credsPath if args.credsPath else CREDSPATH

    if module == "ec2":
        ec2= Ec2Helper(profile, region, KeyFolder, filters)
        ec2.start()
    if module == "session":
        session= SessionHelper(profile, region, configPath, credsPath)
        session.start()
    return

def parse_tuple_arg(arg_string):
    try:
        result = []
        for item in arg_string.split(','):
            values = item.split(':')
            result.append((str(values[0]), str(values[1])))
        return result
    except:
        raise argparse.ArgumentTypeError('Invalid tuple format. Must be "int:int"')
    
if __name__ == "__main__":
    main()