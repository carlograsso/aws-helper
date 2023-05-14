import boto3
import os
import sys
from tabulate import tabulate
import utils
import copy

class Ec2Helper:
    def __init__(self, profile, region, keyFolder, filters):
        self.profile = profile
        self.region = region
        self.keyFolder = keyFolder
        self.all_instances = []
        self.instances = []
        self.chosen_instance = None
        self.filters = filters
        self.session=boto3.Session(profile_name = self.profile if self.profile else None, region_name=self.region)

    def start(self):
        while True:
            self.getEc2Instances()
            self.ec2ActionPrompt()
        return


    def startSsmSession(self):
        print(f"Starting ssm session with instance - {self.chosen_instance['Name']} - {self.chosen_instance['InstanceId']}")
        command = f"aws ssm start-session {f'--profile {self.profile}' if self.profile else ''} --target {self.chosen_instance['InstanceId']} --region {self.chosen_instance['Az'][:-1]}"
        os.system(command)
        return

    def startSshSession(self,loginType):
        instanceId=self.chosen_instance['InstanceId']
        keyName=self.chosen_instance["KeyName"]
        user= input(f"Ec2 instance user to connect to [ec2-user]: ") or "ec2-user"
        if loginType == "key":
            key_subfolder= input(f"Ssh keys subfolder name inside {self.keyFolder}. [None]: ") 

        if self.chosen_instance['PrivateIpAddress'] and self.chosen_instance['PublicIpAddress']:
            print("Choose one:")
            print("1 - SSH to PrivateIp")
            print("2 - SSH to PublicIp")
            choice = utils.choiceEvaluator(3)
            usePrivate = True if int(choice) == 1 else False 
        elif self.chosen_instance['PrivateIpAddress']:
            usePrivate = True
        elif self.chosen_instance['PublicIpAddress']:
            usePrivate = False  
        ip=self.chosen_instance[f"{'Private' if usePrivate else 'Public'}IpAddress"]
        print(f"Starting ssh session with instance - {self.chosen_instance['Name']} - {instanceId} - {user}@{ip} - {f'using ssh key {self.keyFolder}/{key_subfolder}/{keyName}' if loginType == 'key' else 'with password authentication'}")
        command=f"ssh {f'-i {self.keyFolder}/{key_subfolder}/{keyName}' if loginType == 'key' else ''} {user}@{ip}"
        os.system(command)
        return

    def getEc2Instances(self, refresh=True):
        if refresh:
            self.all_instances = []
            ec2 = self.session.client('ec2')
            # usa il metodo describe_instances per ottenere un elenco di tutte le istanze EC2 
            response = ec2.describe_instances()
            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    name_tags=[tag["Value"] for tag in instance["Tags"] if tag["Key"] == "Name"]
                    new_instance={
                        "Index"             : len(self.all_instances)+1,
                        "Name"              : name_tags[0] if name_tags else None,
                        "InstanceId"        : instance["InstanceId"],
                        "InstanceType"      : instance["InstanceType"],
                        "KeyName"           : instance["KeyName"] if "KeyName" in instance else None,
                        "VpcId"             : instance["VpcId"],
                        "SubnetId"          : instance["SubnetId"],
                        "Az"                : instance["Placement"]["AvailabilityZone"],
                        "PrivateIpAddress"  : instance["PrivateIpAddress"],
                        "PublicIpAddress"   : instance["PublicIpAddress"] if "PublicIpAddress" in instance else None,
                        "State"             : instance["State"]["Name"]
                    }
                    self.all_instances.append(new_instance)
        self.filterInstances()
        self.ec2ListPrompt()
        return

    def ec2ActionPrompt(self):
        print("######################################## Action")
        print("Selected Instance")
        print(tabulate([self.chosen_instance], headers="keys", tablefmt="grid", maxcolwidths=[None,20]))
        print("Choose one Action:")
        print("1) SSM session")
        print("2) SSH with Key")
        print("3) SSH with Password")
        print("q) to Quit")
        print("b) to go Back")
        choice = utils.choiceEvaluator([3,"b","q"])
        if choice == "q":
            sys.exit()
        elif choice == "b":
            return 
        elif int(choice) == 1:
            self.startSsmSession()
        elif int(choice) == 2:
            self.startSshSession("key")
        elif int(choice) == 3:
            self.startSshSession("password") 

    def ec2ListPrompt(self):
        print("######################################## EC2 List")
        print(f"Active Filters: {self.filters}")
        print(tabulate(self.instances, headers="keys", tablefmt="grid", maxcolwidths=[None,20]))
        print("Type: ")
        print('f) to change filters')
        print('r) to reload instances list')
        print('q) to Quit')
        print("Or select an instance Index to connect") 
        choice = utils.choiceEvaluator([len(self.instances),"f","q","r"])
        if choice == "f":
            self.changeFilters()
        elif choice == "q":
            sys.exit()
        elif choice == "r":
            self.getEc2Instances()
        elif int(choice) in range(len(self.instances)+1):
            self.chosen_instance=self.instances[int(choice)-1]
        return 
    
    def filterInstances(self):
        self.instances = [inst for inst in self.all_instances]
        if not self.filters:
            return

        for filter_name, filter_value in self.filters:
            self.instances = [inst for inst in self.instances if inst.get(filter_name) and filter_value in inst[filter_name]]
    
    def changeFilters(self):
        print("######################################## Filters")
        self.showFilters()
        print("Type:")
        print('a) to add filters')
        print('b) to go back')
        print('q) to quit')
        if self.filters:
            print("Or insert a filter index to remove it")

        choice = utils.choiceEvaluator([len(self.filters) if self.filters else None, "a", "b", "q"])
        print(choice)

        if choice == "a":
            new_filter = input("Insert filter (format key:value): ")
            if not self.filters:
                self.filters = []
            self.filters.append((new_filter.split(":")[0], new_filter.split(":")[1]))
            self.changeFilters()

        elif choice == "b":
            self.getEc2Instances(refresh=False)

        elif choice == "q":
            sys.exit()

        elif int(choice) in range(1, len(self.filters) + 1):
            del self.filters[int(choice)-1]
            self.changeFilters()
    
    def showFilters(self):
        if self.filters:
            print("Active filters:")
            for index, filter in enumerate(self.filters, 1):
                print(f"{index}) {filter}")
        else:
            print("No active filters")